from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING

from config import (
    ROLE_BALANCE, ROLE_EMOJI, ROLE_NAMES, GIFS,
    MIN_PLAYERS, MAX_PLAYERS, RoleDistribution,
)

if TYPE_CHECKING:
    pass


def generate_game_id() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def get_role_emoji(role_name: str) -> str:
    return ROLE_EMOJI.get(role_name, "❓")


def get_role_name(role_name: str) -> str:
    return ROLE_NAMES.get(role_name, "Неизвестно")


def get_gif(category: str) -> str:
    return GIFS.get(category, GIFS["night"])


def get_distribution(player_count: int) -> RoleDistribution:
    if player_count < MIN_PLAYERS:
        player_count = MIN_PLAYERS
    if player_count > MAX_PLAYERS:
        player_count = MAX_PLAYERS
    return ROLE_BALANCE[player_count]


def build_role_list(distribution: RoleDistribution) -> list[str]:
    roles = []
    for role_name in ["mafia", "sheriff", "doctor", "seer", "maniac", "kamikaze", "merchant", "bartender", "town"]:
        count = getattr(distribution, role_name, 0)
        for _ in range(count):
            roles.append(role_name)
    return roles


def shuffle_roles(player_count: int) -> list[str]:
    dist = get_distribution(player_count)
    roles = build_role_list(dist)
    random.shuffle(roles)
    return roles[:player_count]


def format_lobby(player_ids: list[int], player_names: dict[int, str]) -> str:
    lines = ["🎭 **ЛОББИ МАФИИ**\n"]
    for i, uid in enumerate(player_ids, 1):
        name = player_names.get(uid, f"Игрок {uid}")
        lines.append(f"  {i}. {name}")
    lines.append(f"\nИгроков: {len(player_ids)}")
    return "\n".join(lines)


def format_role_reveal(role_name: str) -> str:
    emoji = get_role_emoji(role_name)
    name = get_role_name(role_name)
    from config import ROLE_DESCRIPTIONS
    desc = ROLE_DESCRIPTIONS.get(role_name, "")
    return f"{emoji} **Твоя роль: {name}**\n\n{desc}"


def format_day_result(killed_ids: list[int], player_names: dict[int, str], killed_roles: dict[int, str]) -> str:
    if not killed_ids:
        return "🌅 Никто не погиб этой ночью!"
    lines = ["🌅 Результаты ночи:\n"]
    for uid in killed_ids:
        name = player_names.get(uid, f"Игрок {uid}")
        role = killed_roles.get(uid, "???")
        emoji = get_role_emoji(role)
        role_name = get_role_name(role)
        lines.append(f"  💀 {name} погиб — {emoji} {role_name}")
    return "\n".join(lines)


def format_role_list_summary(players: dict[int, object]) -> str:
    from collections import Counter
    role_counts = Counter()
    for p in players.values():
        if hasattr(p, "role"):
            role_counts[p.role.name] += 1
    lines = ["🎭 **Состав комнаты:**\n"]
    for role, count in role_counts.most_common():
        emoji = get_role_emoji(role)
        name = get_role_name(role)
        lines.append(f"  {emoji} {name} × {count}")
    return "\n".join(lines)


def check_win_condition(alive_roles: list[str]) -> str | None:
    mafia_alive = sum(1 for r in alive_roles if r == "mafia")
    town_alive = sum(1 for r in alive_roles if r != "mafia")
    if mafia_alive == 0:
        return "town"
    if mafia_alive >= town_alive:
        return "mafia"
    return None
