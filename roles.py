from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game import Game


class Role(ABC):
    name: str = "base"
    team: str = "town"  # "town", "mafia", "neutral"
    can_act_at_night: bool = True

    def __init__(self):
        self.target: Optional[int] = None
        self.acted: bool = False

    def reset_night(self):
        self.target = None
        self.acted = False

    @abstractmethod
    def get_action_text(self, game: Game, player_id: int) -> str:
        pass

    @abstractmethod
    def resolve(self, game: Game, player_id: int) -> list[str]:
        """Возвращает список сообщений о результатах."""
        pass


class Mafia(Role):
    name = "mafia"
    team = "mafia"

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "🔪 Выберите цель для убийства:"

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.target is None:
            return ["Мафия не выбрала цель."]
        target_name = game.players[self.target].display_name
        return [f"Мафия выбрала цель: {target_name}"]


class Sheriff(Role):
    name = "sheriff"
    team = "town"

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "🔍 Кого проверить? Мафия или нет?"

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.target is None:
            return ["Шериф не проверил никого."]
        target_role = game.players[self.target].role
        is_mafia = target_role.team == "mafia"
        result = "ДА — это МАФИЯ!" if is_mafia else "НЕТ — не мафия."
        game.pending_messages.append((player_id, f"🔍 Результат проверки: {game.players[self.target].display_name} — {result}"))
        return []


class Doctor(Role):
    name = "doctor"
    team = "town"
    last_healed: Optional[int] = None

    def reset_night(self):
        super().reset_night()
        # last_healed НЕ сбрасывается

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "💊 Кого спасти сегодня ночью?"

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.target is None:
            return ["Доктор не вылечил никого."]
        if self.target == self.last_healed and self.last_healed is not None:
            game.pending_messages.append((player_id, "⚠️ Вы не можете лечить одного игрока 2 раза подряд!"))
            self.target = None
            return []
        self.last_healed = self.target
        return []


class Seer(Role):
    name = "seer"
    team = "town"

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "🔮 Кого проверить? Узнаете точную роль."

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.target is None:
            return ["Провидец не проверил никого."]
        target_role = game.players[self.target].role
        from config import ROLE_NAMES
        role_name = ROLE_NAMES.get(target_role.name, "Неизвестно")
        game.pending_messages.append((player_id, f"🔮 {game.players[self.target].display_name} — это: {role_name}"))
        return []


class Maniac(Role):
    name = "maniac"
    team = "neutral"
    has_killed = False

    def reset_night(self):
        super().reset_night()
        # has_killed НЕ сбрасывается

    def get_action_text(self, game: Game, player_id: int) -> str:
        if self.has_killed:
            return "🗡️ Вы уже использовали свой выстрел."
        return "🗡️ Кого убить? (Один раз за игру)"

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.has_killed:
            return []
        if self.target is None:
            return ["Маньяк не стрелял."]
        self.has_killed = True
        target = game.players[self.target]
        return [f"🗡️ Маньяк убил {target.display_name}!"]


class Kamikaze(Role):
    name = "kamikaze"
    team = "town"

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "💣 Ты Камикадзе. Жди ночи..."

    def resolve(self, game: Game, player_id: int) -> list[str]:
        return []

    def on_killed_by_mafia(self, game: Game) -> Optional[int]:
        """Возвращает ID одного мафиози для взрыва, или None."""
        mafia_ids = [
            uid for uid, p in game.players.items()
            if p.role.name == "mafia" and p.alive and uid != game.current_night_killer
        ]
        if mafia_ids:
            import random
            return random.choice(mafia_ids)
        return None


class Merchant(Role):
    name = "merchant"
    team = "town"
    coins: int = 100
    shield_active: bool = False

    def reset_night(self):
        super().reset_night()
        self.shield_active = False

    def get_action_text(self, game: Game, player_id: int) -> str:
        from config import MERCHANT_ITEMS
        lines = [f"💰 Баланс: {self.coins} монет", "Покупки:"]
        for key, item in MERCHANT_ITEMS.items():
            affordable = "✅" if self.coins >= item["cost"] else "❌"
            lines.append(f"  {item['emoji']} {item['name']} — {item['cost']} {affordable}")
        lines.append("\nКупить: нажмите кнопку или пропустите.")
        return "\n".join(lines)

    def resolve(self, game: Game, player_id: int) -> list[str]:
        return []


class Bartender(Role):
    name = "bartender"
    team = "town"
    swapped_role: Optional[str] = None

    def reset_night(self):
        super().reset_night()
        self.swapped_role = None

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "🍸 Кого \"взломать\"? Выберите игрока, роль которого подменится на случайную (на эту ночь)."

    def resolve(self, game: Game, player_id: int) -> list[str]:
        if self.target is None:
            return ["Бармен никого не взломал."]
        return [f"Бармен подменил роль {game.players[self.target].display_name}"]


class Town(Role):
    name = "town"
    team = "town"
    can_act_at_night = False

    def get_action_text(self, game: Game, player_id: int) -> str:
        return "👤 Ты мирный житель. Ночью отдыхай, днём голосуй."

    def resolve(self, game: Game, player_id: int) -> list[str]:
        return []


ROLE_MAP = {
    "mafia": Mafia,
    "sheriff": Sheriff,
    "doctor": Doctor,
    "seer": Seer,
    "maniac": Maniac,
    "kamikaze": Kamikaze,
    "merchant": Merchant,
    "bartender": Bartender,
    "town": Town,
}


def create_role(name: str) -> Role:
    cls = ROLE_MAP.get(name)
    if cls is None:
        raise ValueError(f"Unknown role: {name}")
    return cls()
