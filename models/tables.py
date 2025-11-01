from dataclasses import dataclass
from typing import Any, Mapping, ClassVar
from datetime import datetime

@dataclass(frozen=True)
class Table:
    """Доменная модель стола (упрощённая)."""
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
        """Создаёт Table из строки БД (dict)."""
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
        """Параметры для INSERT."""
        return (
            self.number,
            self.capacity,
            self.zone,
            self.status,
            self.notes,
        )

    def to_update_params(self) -> tuple[Any, ...]:
        """Параметры для UPDATE (последний элемент — id)."""
        return (
            self.number,
            self.capacity,
            self.zone,
            self.status,
            self.notes,
            self.id,
        )