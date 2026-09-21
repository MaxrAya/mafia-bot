from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
PLAYERS_FILE = DATA_DIR / "players.json"
GAMES_FILE = DATA_DIR / "games.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===== Players =====

def get_player(user_id: int) -> Optional[dict]:
    data = _load_json(PLAYERS_FILE)
    return data.get(str(user_id))


def save_player(user_id: int, name: str) -> dict:
    data = _load_json(PLAYERS_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "name": name,
            "games_played": 0,
            "wins": 0,
            "kills": 0,
            "deaths": 0,
            "role_stats": {},
        }
    else:
        data[uid]["name"] = name
    _save_json(PLAYERS_FILE, data)
    return data[uid]


def update_player_stats(user_id: int, role_name: str, won: bool, kills: int = 0, died: bool = False):
    data = _load_json(PLAYERS_FILE)
    uid = str(user_id)
    if uid not in data:
        return

    player = data[uid]
    player["games_played"] = player.get("games_played", 0) + 1
    if won:
        player["wins"] = player.get("wins", 0) + 1
    player["kills"] = player.get("kills", 0) + kills
    if died:
        player["deaths"] = player.get("deaths", 0) + 1

    role_stats = player.setdefault("role_stats", {})
    rs = role_stats.setdefault(role_name, {"played": 0, "wins": 0})
    rs["played"] += 1
    if won:
        rs["wins"] += 1

    _save_json(PLAYERS_FILE, data)


def get_top_players(limit: int = 10) -> list[dict]:
    data = _load_json(PLAYERS_FILE)
    players = []
    for uid, info in data.items():
        played = info.get("games_played", 0)
        if played > 0:
            players.append({
                "user_id": int(uid),
                "name": info["name"],
                "games_played": played,
                "wins": info.get("wins", 0),
                "winrate": round(info.get("wins", 0) / played * 100, 1),
            })
    players.sort(key=lambda x: x["wins"], reverse=True)
    return players[:limit]


# ===== Games =====

def save_game_result(game_data: dict):
    data = _load_json(GAMES_FILE)
    game_id = game_data["game_id"]
    data[game_id] = game_data
    _save_json(GAMES_FILE, data)


def get_game_result(game_id: str) -> Optional[dict]:
    data = _load_json(GAMES_FILE)
    return data.get(game_id)
