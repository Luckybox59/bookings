"""
Этот модуль определяет модель данных для пользователя.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, ClassVar

@dataclass(frozen=True)
class User:
    """
    Представляет пользователя системы.

    Attributes:
        __table__: Название таблицы в базе данных.
        __fkeys__: Внешние ключи для таблицы (в данном случае отсутствуют).
        id: Уникальный идентификатор пользователя.
        email: Адрес электронной почты пользователя.
        full_name: Полное имя пользователя.
        phone: Номер телефона пользователя.
        created_at: Время создания записи.
        updated_at: Время последнего обновления записи.
    """
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
        """
        Создает объект User из строки данных, полученной из базы данных.

        Args:
            row: Словарь с данными строки.

        Returns:
            Экземпляр класса User.
        """
        return User(
            id=row.get("id"),
            email=row.get("email"),
            full_name=row.get("full_name"),
            phone=row.get("phone"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_insert_params(self) -> tuple[Any, ...]:
        """
        Возвращает кортеж параметров для вставки новой записи в базу данных.

        Returns:
            Кортеж со значениями полей для SQL-запроса INSERT.
        """
        return (
            self.email,
            self.full_name,
            self.phone,
        )

    def to_update_params(self) -> tuple[Any, ...]:
        """
        Возвращает кортеж параметров для обновления существующей записи в базе данных.

        Returns:
            Кортеж со значениями полей для SQL-запроса UPDATE.
        """
        return (
            self.email,
            self.full_name,
            self.phone,
            self.id,
        )