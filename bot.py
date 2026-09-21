from __future__ import annotations

import asyncio
import logging
import random
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ChatPermissions,
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode, ChatType
from aiogram.exceptions import TelegramBadRequest

from config import (
    BOT_TOKEN, GIFS, NIGHT_TIMEOUT, DAY_TIMEOUT,
    VOTE_TIMEOUT, LOBBY_TIMEOUT, MIN_PLAYERS, MAX_PLAYERS,
    MERCHANT_ITEMS, ROLE_EMOJI, ROLE_NAMES, ROLE_DESCRIPTIONS,
)
from game import Game, GamePhase, PlayerState
from utils import (
    generate_game_id, get_gif, format_lobby,
    format_role_reveal, format_role_list_summary,
    get_role_name, get_role_emoji,
)
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

games: dict[str, Game] = {}
user_game: dict[int, str] = {}
chat_game: dict[int, str] = {}

MUTED_PERMS = ChatPermissions(can_send_messages=False, can_send_audios=False, can_send_documents=False,
                               can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
                               can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
                               can_add_web_page_previews=False, can_invite_users=False, can_change_info=False,
                               can_pin_messages=False, can_manage_topics=False)

UNMUTED_PERMS = ChatPermissions(can_send_messages=True, can_send_audios=True, can_send_documents=True,
                                  can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                                  can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                                  can_add_web_page_previews=True, can_invite_users=True, can_change_info=False,
                                  can_pin_messages=False, can_manage_topics=False)


async def send_message(target_id: int, text: str, gif_url: Optional[str] = None, targetable: Optional[dict] = None):
    try:
        if gif_url:
            try:
                await bot.send_animation(target_id, animation=gif_url, caption=text)
            except TelegramBadRequest:
                await bot.send_message(target_id, text)
        else:
            await bot.send_message(target_id, text, reply_markup=None)
    except Exception as e:
        logger.error(f"Failed to send message to {target_id}: {e}")


async def mute_chat(chat_id: int, mute: bool):
    try:
        perms = MUTED_PERMS if mute else UNMUTED_PERMS
        await bot.set_chat_permissions(chat_id, perms)
    except Exception as e:
        logger.error(f"Failed to mute chat {chat_id}: {e}")


async def send_target_keyboard(user_id: int, text: str, targetable: dict[int, PlayerState]):
    buttons = []
    row = []
    for uid, ps in targetable.items():
        row.append(InlineKeyboardButton(text=f"{ps.display_name}", callback_data=f"target:{uid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Skip", callback_data="target:none")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await bot.send_message(user_id, text, reply_markup=markup)
    except Exception as e:
        logger.error(f"Failed to send keyboard to {user_id}: {e}")


# ==================== HANDLERS ====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    name = message.from_user.first_name or "Player"
    db.save_player(user_id, name)
    await message.answer(
        f"Hello, <b>{name}</b>!\n\n"
        "I'm a <b>Mafia</b> bot.\n\n"
        "Commands:\n"
        "/newgame - create game\n"
        "/join - join game\n"
        "/leave - leave game\n"
        "/start_game - start game\n"
        "/profile - your profile\n"
        "/stats - top players\n"
        "/rules - rules\n",
    )


@router.message(Command("rules"))
async def cmd_rules(message: Message):
    await message.answer(
        "<b>Mafia Rules</b>\n\n"
        "<b>Night:</b>\n"
        "- Mafia picks a target\n"
        "- Sheriff checks a player\n"
        "- Doctor saves a player\n"
        "- Seer sees a role\n"
        "- Maniac can kill (once)\n"
        "- Bartender swaps role (one night)\n"
        "- Merchant buys items\n\n"
        "<b>Day:</b>\n"
        "- Discussion and voting\n"
        "- Most votes = execution\n\n"
        "<b>Win:</b>\n"
        "- Town: mafia = 0\n"
        "- Mafia: mafia >= town\n\n"
        "<b>Special roles:</b>\n"
        "Kamikaze - explodes when killed\n"
        "Merchant - earns coins\n"
        "Bartender - swaps roles\n",
    )


@router.message(Command("newgame"))
async def cmd_newgame(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if chat_id in chat_game:
        existing = games.get(chat_game[chat_id])
        if existing and existing.phase == GamePhase.LOBBY:
            await message.answer("Game already exists! /join to join.")
            return

    game_id = generate_game_id()
    game = Game(
        game_id=game_id,
        chat_id=chat_id,
        creator_id=user_id,
        message_sender=send_message,
    )
    game.add_player(user_id, message.from_user.first_name or "Player")
    games[game_id] = game
    user_game[user_id] = game_id
    chat_game[chat_id] = game_id

    await message.answer(
        f"<b>NEW GAME CREATED!</b>\n\n"
        f"ID: <code>{game_id}</code>\n"
        f"Creator: {message.from_user.first_name}\n\n"
        f"Waiting for players! Minimum {MIN_PLAYERS}.\n"
        f"/join - join\n"
        f"/start_game - start",
    )


@router.message(Command("join"))
async def cmd_join(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    name = message.from_user.first_name or "Player"

    if chat_id not in chat_game:
        await message.answer("No active game. Create: /newgame")
        return

    game_id = chat_game[chat_id]
    game = games.get(game_id)
    if not game or game.phase != GamePhase.LOBBY:
        await message.answer("Game already started or not found.")
        return

    if user_id in game.players:
        await message.answer("You are already in the game!")
        return

    if not game.add_player(user_id, name):
        await message.answer("Lobby full (max 16).")
        return

    user_game[user_id] = game_id
    lobby_text = format_lobby(game.lobby_order, {uid: game.players[uid].display_name for uid in game.players})
    lobby_text = lobby_text.replace("**", "")
    await message.answer(
        f"<b>{name}</b> joined!\n\n"
        f"{lobby_text}\n\n"
        f"/join - more players\n/start_game - start",
    )


@router.message(Command("leave"))
async def cmd_leave(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if chat_id not in chat_game:
        await message.answer("You are not in a game.")
        return

    game_id = chat_game[chat_id]
    game = games.get(game_id)
    if not game or game.phase != GamePhase.LOBBY:
        await message.answer("Game already started.")
        return

    if user_id not in game.players:
        await message.answer("You are not in the game.")
        return

    if user_id == game.creator_id:
        await message.answer("Creator cannot leave. Use /cancel.")
        return

    game.remove_player(user_id)
    user_game.pop(user_id, None)
    await message.answer(
        f"{message.from_user.first_name} left the game.\n"
        f"Players: {len(game.players)}",
    )


@router.message(Command("start_game"))
async def cmd_start_game(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if chat_id not in chat_game:
        await message.answer("No active game.")
        return

    game_id = chat_game[chat_id]
    game = games.get(game_id)
    if not game or game.phase != GamePhase.LOBBY:
        await message.answer("Game already started.")
        return

    if user_id != game.creator_id:
        await message.answer("Only the creator can start the game.")
        return

    if len(game.players) < MIN_PLAYERS:
        await message.answer(f"Need at least {MIN_PLAYERS} players!")
        return

    if not game.start_game():
        await message.answer("Failed to start game.")
        return

    await message.answer(
        "<b>GAME STARTS!</b>\n\n"
        "Roles have been dealt. Check your DMs!\n\n"
        "Night is falling...\n"
        "Everyone be QUIET - talking at night is forbidden!\n",
        reply_markup=None,
    )

    try:
        await bot.send_animation(chat_id, animation=get_gif("night"), caption="Night is falling...")
    except TelegramBadRequest:
        await bot.send_message(chat_id, "Night is falling...")

    await mute_chat(chat_id, True)

    for uid, ps in game.players.items():
        role_text = format_role_reveal(ps.role.name)
        role_text = role_text.replace("**", "")
        try:
            await bot.send_message(uid, role_text)
        except Exception as e:
            logger.error(f"Could not send role to {uid}: {e}")

    await asyncio.sleep(2)
    await start_night(game)


async def start_night(game: Game):
    game.reset_all_roles_night()
    game.phase = GamePhase.NIGHT
    game.killed_this_night.clear()

    for uid, ps in game.get_alive_players().items():
        role = ps.role
        if not role.can_act_at_night:
            continue
        text = role.get_action_text(game, uid)
        targetable = game.get_targetable_players(uid)
        if role.name in ["doctor", "bartender", "merchant"]:
            targetable = game.get_alive_players()
        if targetable:
            await send_target_keyboard(uid, text, targetable)

    asyncio.create_task(night_timer(game))


async def night_timer(game: Game):
    await asyncio.sleep(NIGHT_TIMEOUT)

    for uid, ps in game.get_alive_players().items():
        role = ps.role
        if role.can_act_at_night and not role.acted:
            if role.name == "doctor":
                role.target = None
            elif role.name == "bartender":
                role.target = None
            elif role.name == "maniac" and not role.has_killed:
                role.target = None
            else:
                alive = game.get_alive_players()
                alive.pop(uid, None)
                if alive:
                    role.target = random.choice(list(alive.keys()))
                    role.acted = True

    result = await game.resolve_night()

    winner = game.check_winner()
    if winner:
        await end_game(game, winner)
        return

    await asyncio.sleep(3)
    game.start_day()

    await mute_chat(game.chat_id, False)

    alive_players = game.get_alive_players()
    buttons = []
    row = []
    for uid, ps in alive_players.items():
        row.append(InlineKeyboardButton(text=ps.display_name, callback_data=f"vote:{uid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Skip", callback_data="vote:none")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    alive_list = "\n".join(f"  {get_role_emoji(ps.role.name)} {ps.display_name}" for uid, ps in alive_players.items())
    await bot.send_message(
        game.chat_id,
        f"<b>DAY {game.day_number}</b>\n\n"
        f"Discuss and vote!\n"
        f"Voting for execution:\n"
        f"Time: {VOTE_TIMEOUT} seconds.\n\n"
        f"Alive players:\n{alive_list}",
        reply_markup=markup,
    )

    asyncio.create_task(day_timer(game))


async def day_timer(game: Game):
    await asyncio.sleep(VOTE_TIMEOUT)
    await resolve_day(game)


async def resolve_day(game: Game):
    killed_uid = game.resolve_day_vote()

    if killed_uid and killed_uid in game.players:
        ps = game.players[killed_uid]
        role = ps.role
        try:
            await bot.send_animation(
                game.chat_id,
                animation=get_gif("lynch"),
                caption=(
                    f"<b>EXECUTION</b>\n\n"
                    f"{ps.display_name} was executed!\n"
                    f"Role: {get_role_emoji(role.name)} {get_role_name(role.name)}"
                ),
            )
        except TelegramBadRequest:
            await bot.send_message(
                game.chat_id,
                f"<b>EXECUTION</b>\n\n{ps.display_name} was executed!\n"
                f"Role: {get_role_emoji(role.name)} {get_role_name(role.name)}",
            )
    else:
        await bot.send_message(
            game.chat_id,
            "Nobody was executed (no majority).",
        )

    winner = game.check_winner()
    if winner:
        await end_game(game, winner)
        return

    await asyncio.sleep(2)
    await start_night(game)


async def end_game(game: Game, winner: str):
    game.phase = GamePhase.ENDED

    await mute_chat(game.chat_id, False)

    if winner == "mafia":
        title = "MAFIA WINS!"
        gif = get_gif("victory_mafia")
    else:
        title = "TOWN WINS!"
        gif = get_gif("victory_town")

    role_summary = format_role_list_summary(game.players)
    role_summary = role_summary.replace("**", "")
    await bot.send_message(game.chat_id, f"<b>{title}</b>")
    await bot.send_animation(game.chat_id, animation=gif, caption=role_summary)

    for uid, ps in game.players.items():
        won = (winner == "mafia" and ps.role.team == "mafia") or \
              (winner == "town" and ps.role.team != "mafia")
        db.update_player_stats(uid, ps.role.name, won, died=not ps.alive)

    chat_game.pop(game.chat_id, None)
    for uid in list(game.players.keys()):
        user_game.pop(uid, None)
    games.pop(game.game_id, None)


@router.callback_query(F.data.startswith("target:"))
async def cb_target(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split(":")
    target = data[1]

    if user_id not in user_game:
        await callback.answer("Game not found.", show_alert=True)
        return

    game_id = user_game[user_id]
    game = games.get(game_id)
    if not game or game.phase != GamePhase.NIGHT:
        await callback.answer("It is not night.", show_alert=True)
        return

    ps = game.players.get(user_id)
    if not ps or not ps.alive:
        await callback.answer("You are dead.", show_alert=True)
        return

    role = ps.role
    if not role.can_act_at_night or role.acted:
        await callback.answer("Already acted.", show_alert=True)
        return

    if target == "none":
        role.acted = True
        await callback.message.edit_text("Action skipped.")
        await callback.answer()
        return

    target_id = int(target)
    if target_id not in game.get_alive_players():
        await callback.answer("Player unavailable.", show_alert=True)
        return

    role.target = target_id
    role.acted = True

    if isinstance(role, Merchant):
        pass
    elif isinstance(role, Bartender):
        pass

    await callback.message.edit_text(f"Selected: {game.players[target_id].display_name}")
    await callback.answer()


@router.callback_query(F.data.startswith("vote:"))
async def cb_vote(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split(":")
    target = data[1]

    if user_id not in user_game:
        await callback.answer("Game not found.", show_alert=True)
        return

    game_id = user_game[user_id]
    game = games.get(game_id)
    if not game or game.phase != GamePhase.DAY_VOTE:
        await callback.answer("It is not day.", show_alert=True)
        return

    ps = game.players.get(user_id)
    if not ps or not ps.alive:
        await callback.answer("You are dead.", show_alert=True)
        return

    if target == "none":
        await callback.message.edit_text("Vote skipped.")
        await callback.answer()
        return

    target_id = int(target)
    if target_id not in game.get_alive_players():
        await callback.answer("Player unavailable.", show_alert=True)
        return

    if game.cast_vote(user_id, target_id):
        await callback.message.edit_text(f"Voted for: {game.players[target_id].display_name}")
    await callback.answer()


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    player = db.get_player(user_id)
    if not player:
        db.save_player(user_id, message.from_user.first_name or "Player")
        player = db.get_player(user_id)

    played = player.get("games_played", 0)
    wins = player.get("wins", 0)
    winrate = round(wins / played * 100, 1) if played > 0 else 0

    lines = [
        f"<b>Profile: {player['name']}</b>\n",
        f"Games: {played}",
        f"Wins: {wins}",
        f"Winrate: {winrate}%",
        f"Deaths: {player.get('deaths', 0)}",
        f"Kills: {player.get('kills', 0)}",
        "\n<b>Roles:</b>",
    ]

    role_stats = player.get("role_stats", {})
    for role_name, stats in role_stats.items():
        emoji = get_role_emoji(role_name)
        name = get_role_name(role_name)
        wr = round(stats["wins"] / stats["played"] * 100) if stats["played"] > 0 else 0
        lines.append(f"  {emoji} {name}: {stats['played']} games, {wr}% wins")

    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    top = db.get_top_players(10)
    if not top:
        await message.answer("No stats yet. Play a game!")
        return

    lines = ["<b>TOP PLAYERS</b>\n"]
    medals = ["1st", "2nd", "3rd"]
    for i, p in enumerate(top):
        medal = medals[i] if i < 3 else f"  {i+1}."
        lines.append(f"{medal} <b>{p['name']}</b> - {p['wins']} wins ({p['winrate']}%)")

    await message.answer("\n".join(lines))


def setup():
    dp.include_router(router)


def start_bot():
    setup()
    from aiogram import Dispatcher
    dp.run_polling(bot)
