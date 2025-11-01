"""
Этот модуль определяет модель данных для бронирования.
"""
from dataclasses import dataclass
from typing import Any, Mapping, ClassVar
from datetime import datetime

@dataclass(frozen=True)
class Booking:
    """
    Представляет бронирование стола в ресторане.

    Attributes:
        __table__: Название таблицы в базе данных.
        __fkeys__: Внешние ключи для таблицы.
        id: Уникальный идентификатор бронирования.
        user_id: ID пользователя, совершившего бронирование.
        table_id: ID забронированного стола.
        starts_at: Время начала бронирования.
        ends_at: Время окончания бронирования.
        guest_count: Количество гостей.
        status: Статус бронирования (например, 'Ожидание', 'Подтверждено', 'Отменено').
        contact_name: Имя контактного лица.
        contact_phone: Телефон контактного лица.
        notes: Дополнительные заметки к бронированию.
        created_at: Время создания записи.
        updated_at: Время последнего обновления записи.
    """
    __table__: ClassVar[str] = "bookings"
    __fkeys__: ClassVar[dict[str, tuple[str, str, str]]] = {
        "user_id": ("users", "id", "CASCADE"),
        "table_id": ("tables", "id", "RESTRICT"),
    }
    id: int | None
    user_id: int | None
    table_id: int | None
    starts_at: datetime | None
    ends_at: datetime | None
    guest_count: int | None
    status: str | None
    contact_name: str | None
    contact_phone: str | None
    notes: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> "Booking":
        """
        Создает объект Booking из строки данных, полученной из базы данных.

        Args:
            row: Словарь с данными строки.

        Returns:
            Экземпляр класса Booking.
        """
        return Booking(
            id=row.get("id"),
            user_id=row.get("user_id"),
            table_id=row.get("table_id"),
            starts_at=row.get("starts_at"),
            ends_at=row.get("ends_at"),
            guest_count=row.get("guest_count"),
            status=row.get("status"),
            contact_name=row.get("contact_name"),
            contact_phone=row.get("contact_phone"),
            notes=row.get("notes"),
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
            self.user_id,
            self.table_id,
            self.starts_at,
            self.ends_at,
            self.guest_count,
            self.status,
            self.contact_name,
            self.contact_phone,
            self.notes,
        )

    def to_update_params(self) -> tuple[Any, ...]:
        """
        Возвращает кортеж параметров для обновления существующей записи в базе данных.

        Returns:
            Кортеж со значениями полей для SQL-запроса UPDATE.
        """
        return (
            self.user_id,
            self.table_id,
            self.starts_at,
            self.ends_at,
            self.guest_count,
            self.status,
            self.contact_name,
            self.contact_phone,
            self.notes,
            self.id,
        )