"""
Этот модуль определяет модель данных для стола в ресторане.
"""
from dataclasses import dataclass
from typing import Any, Mapping, ClassVar
from datetime import datetime

@dataclass(frozen=True)
class Table:
    """
    Представляет стол в ресторане.

    Attributes:
        __table__: Название таблицы в базе данных.
        __fkeys__: Внешние ключи для таблицы (в данном случае отсутствуют).
        id: Уникальный идентификатор стола.
        number: Номер стола.
        capacity: Вместимость стола (количество человек).
        zone: Зона расположения стола (например, 'Основной зал', 'Терраса').
        status: Статус стола (например, 'Активен', 'На обслуживании').
        notes: Дополнительные заметки о столе.
        created_at: Время создания записи.
        updated_at: Время последнего обновления записи.
    """
    __table__: ClassVar[str] = "tables"
    __fkeys__: ClassVar[dict[str, tuple[str, str, str]]] = {}
    id: int | None
    number: int | None
    capacity: int | None
    zone: str | None
    status: str | None
    notes: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> "Table":
        """
        Создает объект Table из строки данных, полученной из базы данных.

        Args:
            row: Словарь с данными строки.

        Returns:
            Экземпляр класса Table.
        """
        return Table(
            id=row.get("id"),
            number=row.get("number"),
            capacity=row.get("capacity"),
            zone=row.get("zone"),
            status=row.get("status"),
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
            self.number,
            self.capacity,
            self.zone,
            self.status,
            self.notes,
        )

    def to_update_params(self) -> tuple[Any, ...]:
        """
        Возвращает кортеж параметров для обновления существующей записи в базе данных.

        Returns:
            Кортеж со значениями полей для SQL-запроса UPDATE.
        """
        return (
            self.number,
            self.capacity,
            self.zone,
            self.status,
            self.notes,
            self.id,
        )