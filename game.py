from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable

from config import (
    NIGHT_TIMEOUT, DAY_TIMEOUT, VOTE_TIMEOUT,
    ROLE_NAMES, ROLE_EMOJI, MERCHANT_ITEMS,
)
from roles import (
    Role, Mafia, Sheriff, Doctor, Seer,
    Maniac, Kamikaze, Merchant, Bartender, Town,
    create_role,
)
from utils import (
    shuffle_roles, generate_game_id, get_gif,
    format_day_result, check_win_condition, get_role_name,
)
import database as db


class GamePhase(Enum):
    LOBBY = "lobby"
    NIGHT = "night"
    DAY_VOTE = "day_vote"
    ENDED = "ended"


@dataclass
class PlayerState:
    user_id: int
    display_name: str
    role: Role
    alive: bool = True
    voted_for: Optional[int] = None
    votes_received: int = 0

    def reset_vote(self):
        self.voted_for = None
        self.votes_received = 0


@dataclass
class Game:
    game_id: str
    chat_id: int
    creator_id: int
    phase: GamePhase = GamePhase.LOBBY
    players: dict[int, PlayerState] = field(default_factory=dict)
    lobby_order: list[int] = field(default_factory=list)
    night_number: int = 0
    day_number: int = 0
    killed_this_night: list[int] = field(default_factory=list)
    pending_messages: list[tuple[int, str]] = field(default_factory=list)
    day_votes: dict[int, int] = field(default_factory=dict)
    message_sender: Optional[Callable[[int, str, Optional[str]], Awaitable[None]]] = None
    mute_sender: Optional[Callable[[int, bool], Awaitable[None]]] = None

    def add_player(self, user_id: int, display_name: str) -> bool:
        if len(self.players) >= 16:
            return False
        if user_id in self.players:
            return False
        self.lobby_order.append(user_id)
        self.players[user_id] = PlayerState(
            user_id=user_id,
            display_name=display_name,
            role=create_role("town"),
        )
        return True

    def remove_player(self, user_id: int) -> bool:
        if user_id not in self.players:
            return False
        self.lobby_order.remove(user_id)
        del self.players[user_id]
        return True

    def start_game(self) -> bool:
        player_count = len(self.lobby_order)
        if player_count < 4:
            return False

        roles = shuffle_roles(player_count)
        random.shuffle(self.lobby_order)

        for i, uid in enumerate(self.lobby_order):
            role_name = roles[i]
            self.players[uid].role = create_role(role_name)

        self.phase = GamePhase.NIGHT
        self.night_number = 1
        return True

    def get_alive_players(self) -> dict[int, PlayerState]:
        return {uid: p for uid, p in self.players.items() if p.alive}

    def get_alive_mafia(self) -> dict[int, PlayerState]:
        return {uid: p for uid, p in self.get_alive_players().items() if p.role.name == "mafia"}

    def get_alive_non_mafia(self) -> dict[int, PlayerState]:
        return {uid: p for uid, p in self.get_alive_players().items() if p.role.name != "mafia"}

    def get_targetable_players(self, viewer_id: int, same_team: bool = False) -> dict[int, PlayerState]:
        alive = self.get_alive_players()
        viewer_role = self.players[viewer_id].role
        if same_team:
            return {uid: p for uid, p in alive.items() if uid != viewer_id and p.role.team == viewer_role.team}
        return {uid: p for uid, p in alive.items() if uid != viewer_id}

    async def resolve_night(self) -> str:
        self.night_number += 1
        mafia_target = None
        doctor_target = None
        maniac_target = None
        shield_active = False

        for uid, ps in self.get_alive_players().items():
            role = ps.role
            if isinstance(role, Mafia) and role.target:
                mafia_target = role.target
            elif isinstance(role, Doctor) and role.target:
                doctor_target = role.target
            elif isinstance(role, Maniac) and not role.has_killed and role.target:
                maniac_target = role.target
            elif isinstance(role, Merchant) and role.shield_active:
                shield_active = True

        killed = []
        killed_roles = {}

        # Doctor saves
        if doctor_target and doctor_target == mafia_target:
            pass
        elif shield_active and mafia_target:
            pass
        elif mafia_target and mafia_target in self.players:
            ps = self.players[mafia_target]
            ps.alive = False
            killed.append(mafia_target)
            killed_roles[mafia_target] = ps.role.name

            # Kamikaze check
            if isinstance(ps.role, Kamikaze):
                kamikaze = ps.role
                bomb_target = kamikaze.on_killed_by_mafia(self)
                if bomb_target and bomb_target in self.players:
                    self.players[bomb_target].alive = False
                    killed.append(bomb_target)
                    killed_roles[bomb_target] = self.players[bomb_target].role.name
                    if self.message_sender:
                        await self.message_sender(self.chat_id, f"💣 Камикадзе взорвался вместе с {self.players[bomb_target].display_name}!", get_gif("bomb"))

        # Maniac kills (independent)
        if maniac_target and maniac_target in self.players and maniac_target not in killed:
            ps = self.players[maniac_target]
            ps.alive = False
            killed.append(mafia_target if maniac_target == mafia_target else maniac_target)
            if maniac_target != mafia_target:
                killed.append(mafia_target if maniac_target != mafia_target else maniac_target)
                killed[-1] = maniac_target
                killed_roles[maniac_target] = ps.role.name
                if self.message_sender:
                    await self.message_sender(self.chat_id, f"🗡️ Маньяк убил {ps.display_name}!", get_gif("maniac_kill"))

        # Sheriff / Seer resolve
        for uid, ps in self.get_alive_players().items():
            result = ps.role.resolve(self, uid)

        # Merchant income
        for uid, ps in self.get_alive_players().items():
            if isinstance(ps.role, Merchant):
                ps.role.coins += 30

        self.killed_this_night = killed

        # Send pending messages
        for target_id, msg in self.pending_messages:
            if self.message_sender:
                await self.message_sender(target_id, msg)
        self.pending_messages.clear()

        result_text = format_day_result(killed, {uid: self.players[uid].display_name for uid in self.players}, killed_roles)
        if self.message_sender:
            await self.message_sender(self.chat_id, result_text, get_gif("day"))

        return result_text

    def start_day(self):
        self.phase = GamePhase.DAY_VOTE
        self.day_number += 1
        for ps in self.get_alive_players().values():
            ps.reset_vote()
        self.day_votes.clear()

    def cast_vote(self, voter_id: int, target_id: int) -> bool:
        if voter_id not in self.get_alive_players():
            return False
        if target_id not in self.get_alive_players():
            return False
        if voter_id == target_id:
            return False

        old_vote = self.day_votes.get(voter_id)
        if old_vote is not None and old_vote in self.players:
            self.players[old_vote].votes_received -= 1

        self.day_votes[voter_id] = target_id
        self.players[target_id].votes_received += 1
        return True

    def resolve_day_vote(self) -> Optional[int]:
        if not self.day_votes:
            return None

        max_votes = 0
        top_player = None
        tied = False

        for uid, ps in self.get_alive_players().items():
            if ps.votes_received > max_votes:
                max_votes = ps.votes_received
                top_player = uid
                tied = False
            elif ps.votes_received == max_votes and max_votes > 0:
                tied = True

        if tied or max_votes == 0:
            return None

        majority = len(self.get_alive_players()) // 2
        if max_votes > majority:
            self.players[top_player].alive = False
            return top_player
        return None

    def check_winner(self) -> Optional[str]:
        alive_roles = [ps.role.name for ps in self.get_alive_players().values()]
        return check_win_condition(alive_roles)

    def get_role_summary(self) -> dict[str, int]:
        from collections import Counter
        counts = Counter()
        for ps in self.players.values():
            counts[ps.role.name] += 1
        return dict(counts)

    def reset_all_roles_night(self):
        for ps in self.get_alive_players().values():
            ps.role.reset_night()

    async def send_night_actions(self):
        for uid, ps in self.get_alive_players().items():
            role = ps.role
            if not role.can_act_at_night:
                continue
            text = role.get_action_text(self, uid)
            targetable = self.get_targetable_players(uid)
            if not targetable and role.name not in ["doctor", "bartender"]:
                continue
            if self.message_sender:
                await self.message_sender(uid, text, None, targetable)
