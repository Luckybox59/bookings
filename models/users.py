from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, ClassVar

@dataclass(frozen=True)
class User:
    """Доменная модель пользователя (упрощённая)."""
    __table__: ClassVar[str] = "users"
    __fkeys__: ClassVar[dict[str, tuple[str, str, str]]] = {}
    id: int | None
    email: str | None
    full_name: str | None
    phone: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> "User":
        """Создаёт User из строки БД (dict)."""
        return User(
            id=row.get("id"),
            email=row.get("email"),
            full_name=row.get("full_name"),
            phone=row.get("phone"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_insert_params(self) -> tuple[Any, ...]:
        """Параметры для INSERT. Порядок должен совпадать с SQL."""
        return (
            self.email,
            self.full_name,
            self.phone,
        )

    def to_update_params(self) -> tuple[Any, ...]:
        """Параметры для UPDATE. Последний элемент — id (WHERE id=%s)."""
        return (
            self.email,
            self.full_name,
            self.phone,
            self.id,
        )