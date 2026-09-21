from dataclasses import dataclass, field
from typing import Dict, Tuple
import os


BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("WARNING: BOT_TOKEN not set! Set it in Railway → Variables")

# GIF URLs для атмосферы
GIFS = {
    "night": "https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif",
    "day": "https://media.giphy.com/media/3o7abKhOpu0NwenH3O/giphy.gif",
    "mafia_kill": "https://media.giphy.com/media/l0HlFOPbS9TvbBCk0/giphy.gif",
    "doctor_save": "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",
    "sheriff_check": "https://media.giphy.com/media/3o7abKBk7bE3Z2dJ7e/giphy.gif",
    "lynch": "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif",
    "victory_mafia": "https://media.giphy.com/media/l0MYGb1LuZ3n7dRnO/giphy.gif",
    "victory_town": "https://media.giphy.com/media/3o6gE8g2GfT2dPCesE/giphy.gif",
    "lobby": "https://media.giphy.com/media/3o7aCTfyhYawMw0BVu/giphy.gif",
    "maniac_kill": "https://media.giphy.com/media/l3vRn5FxBK4s3JQvC/giphy.gif",
    "bomb": "https://media.giphy.com/media/3oEjI1rGzVaHjGGais/giphy.gif",
}

# Таймауты (секунды)
NIGHT_TIMEOUT = 90
DAY_TIMEOUT = 120
VOTE_TIMEOUT = 60
LOBBY_TIMEOUT = 120

MIN_PLAYERS = 4
MAX_PLAYERS = 16


@dataclass
class RoleDistribution:
    mafia: int
    sheriff: int = 0
    doctor: int = 0
    seer: int = 0
    maniac: int = 0
    kamikaze: int = 0
    merchant: int = 0
    bartender: int = 0
    town: int = 0


ROLE_BALANCE: Dict[int, RoleDistribution] = {
    4: RoleDistribution(mafia=1, sheriff=1, doctor=1, town=1),
    5: RoleDistribution(mafia=1, sheriff=1, doctor=1, town=2),
    6: RoleDistribution(mafia=2, sheriff=1, doctor=1, town=2),
    7: RoleDistribution(mafia=2, sheriff=1, doctor=1, seer=1, town=2),
    8: RoleDistribution(mafia=2, sheriff=1, doctor=1, seer=1, town=3),
    9: RoleDistribution(mafia=3, sheriff=1, doctor=1, seer=1, maniac=1, town=2),
    10: RoleDistribution(mafia=3, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, town=2),
    11: RoleDistribution(mafia=3, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, town=2),
    12: RoleDistribution(mafia=3, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, bartender=1, town=2),
    13: RoleDistribution(mafia=4, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, bartender=1, town=2),
    14: RoleDistribution(mafia=4, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, bartender=1, town=3),
    15: RoleDistribution(mafia=4, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, bartender=1, town=4),
    16: RoleDistribution(mafia=5, sheriff=1, doctor=1, seer=1, maniac=1, kamikaze=1, merchant=1, bartender=1, town=4),
}

ROLE_NAMES = {
    "mafia": "Мафия",
    "sheriff": "Шериф",
    "doctor": "Доктор",
    "seer": "Провидец",
    "maniac": "Маньяк",
    "kamikaze": "Камикадзе",
    "merchant": "Купец",
    "bartender": "Бармен",
    "town": "Мирный житель",
}

ROLE_EMOJI = {
    "mafia": "🔪",
    "sheriff": "🔍",
    "doctor": "💊",
    "seer": "🔮",
    "maniac": "🗡️",
    "kamikaze": "💣",
    "merchant": "💰",
    "bartender": "🍸",
    "town": "👤",
}

ROLE_DESCRIPTIONS = {
    "mafia": "Ты — Мафия! Ночью выбери кого убить. Днём притворяйся мирным.",
    "sheriff": "Ты — Шериф! Ночью проверь одного игрока — мафия он или нет.",
    "doctor": "Ты — Доктор! Ночью спаси одного игрока от смерти. Не можешь лечить одного 2 раза подряд.",
    "seer": "Ты — Провидец! Ночью посмотри роль любого игрока.",
    "maniac": "Ты — Маньяк! Однажды за игру убьёшь любого. Мафия — тоже твоя цель.",
    "kamikaze": "Ты — Камикадзе! Если тебя убьёт мафия — взорвёшься и убьёшь одного из них.",
    "merchant": "Ты — Купец! Получаешь монеты. Покупай: инфо (💡), защиту (🛡️), доп. проверку (🔎).",
    "bartender": "Ты — Бармен! Ночью подменяй роль одного игрока случайной на эту ночь.",
    "town": "Ты — Мирный житель! Днём голосуй за казнь подозреваемых.",
}

MERCHANT_ITEMS = {
    "info": {"name": "Информация", "emoji": "💡", "cost": 50, "desc": "Узнай роль игрока (ночь)"},
    "shield": {"name": "Защита", "emoji": "🛡️", "cost": 80, "desc": "Спаси тебя от убийства (ночь)"},
    "extra_check": {"name": "Доп. проверка", "emoji": "🔎", "cost": 60, "desc": "Проверь роль второго игрока (ночь)"},
}
