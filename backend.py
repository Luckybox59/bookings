"""
Этот модуль содержит основную бизнес-логику и функции для взаимодействия с базой данных.

Он предоставляет функции для создания, чтения, обновления и удаления (CRUD)
пользователей, столов и бронирований.
"""
from pg_driver import PGConfig, PGDriver
from models.users import User
from models.tables import Table
from models.booking import Booking
from datetime import datetime
from typing import Any

db = PGDriver(PGConfig.from_env())


def create_tables():
    """
    Инициализирует таблицы в базе данных на основе определенных моделей.
    """
    db.ensure_models([User, Table, Booking])


def _get_id(row: Any) -> int:
    """
    Извлекает ID из результата запроса к базе данных.

    Args:
        row: Строка результата из базы данных.

    Returns:
        ID записи.
    """
    return int(row[0] if not isinstance(row, dict) else row["id"]) if row is not None else 0


def create_user(u: User) -> int:
    """
    Создает нового пользователя в базе данных.

    Args:
        u: Объект пользователя для создания.

    Returns:
        ID нового пользователя.
    """
    sql = "INSERT INTO users(email, full_name, phone) VALUES (%s,%s,%s) RETURNING id"
    with db.transaction() as tx:
        row = tx.fetchone(sql, u.to_insert_params())
        return _get_id(row)


def get_user_by_id(user_id: int) -> User | None:
    """
    Получает пользователя по его ID.

    Args:
        user_id: ID пользователя.

    Returns:
        Объект пользователя или None, если пользователь не найден.
    """
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM users WHERE id=%s", [user_id])
        return User.from_row(row) if row else None


def update_user(u: User) -> int:
    """
    Обновляет данные пользователя.

    Args:
        u: Объект пользователя с обновленными данными.

    Returns:
        Количество обновленных записей.
    """
    sql = "UPDATE users SET email=%s, full_name=%s, phone=%s, updated_at=now() WHERE id=%s"
    with db.transaction() as tx:
        return tx.execute(sql, u.to_update_params())


def delete_user(user_id: int) -> int:
    """
    Удаляет пользователя по ID.

    Args:
        user_id: ID пользователя для удаления.

    Returns:
        Количество удаленных записей.
    """
    with db.transaction() as tx:
        return tx.execute("DELETE FROM users WHERE id=%s", [user_id])


def create_table_rec(t: Table) -> int:
    """
    Создает новую запись о столе в базе данных.

    Args:
        t: Объект стола для создания.

    Returns:
        ID нового стола.
    """
    sql = (
        "INSERT INTO tables(number,capacity,zone,status,notes) "
        "VALUES (%s,%s,%s,%s,%s) RETURNING id"
    )
    with db.transaction() as tx:
        row = tx.fetchone(sql, t.to_insert_params())
        return _get_id(row)


def get_table(table_id: int) -> Table | None:
    """
    Получает информацию о столе по ID.

    Args:
        table_id: ID стола.

    Returns:
        Объект стола или None, если стол не найден.
    """
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM tables WHERE id=%s", [table_id])
        return Table.from_row(row) if row else None


def update_table_rec(t: Table) -> int:
    """
    Обновляет информацию о столе.

    Args:
        t: Объект стола с обновленными данными.

    Returns:
        Количество обновленных записей.
    """
    sql = (
        "UPDATE tables SET number=%s,capacity=%s,zone=%s,status=%s,notes=%s, updated_at=now() WHERE id=%s"
    )
    with db.transaction() as tx:
        return tx.execute(sql, t.to_update_params())


def delete_table(table_id: int) -> int:
    """
    Удаляет стол по ID.

    Args:
        table_id: ID стола для удаления.

    Returns:
        Количество удаленных записей.
    """
    with db.transaction() as tx:
        return tx.execute("DELETE FROM tables WHERE id=%s", [table_id])


def is_table_available(table_id: int, starts_at: datetime, ends_at: datetime, booking_id_to_exclude: int | None = None) -> bool:
    """
    Проверяет, доступен ли стол в указанный промежуток времени.

    Args:
        table_id: ID стола.
        starts_at: Время начала бронирования.
        ends_at: Время окончания бронирования.
        booking_id_to_exclude: ID бронирования, которое нужно исключить из проверки
                               (полезно при обновлении существующего бронирования).

    Returns:
        True, если стол доступен, иначе False.
    """
    params: list[Any] = [table_id, starts_at, ends_at]
    sql = (
        "SELECT 1 FROM bookings "
        "WHERE table_id=%s AND status <> 'canceled' "
        "AND NOT (ends_at <= %s OR starts_at >= %s)"
    )
    if booking_id_to_exclude is not None:
        sql += " AND id<>%s"
        params.append(booking_id_to_exclude)
    with db.connect() as conn:
        row = conn.fetchone(sql, params)
        return row is None


def create_booking(b: Booking) -> int:
    """
    Создает новое бронирование.

    Args:
        b: Объект бронирования для создания.

    Returns:
        ID нового бронирования.

    Raises:
        ValueError: Если стол недоступен в выбранное время.
    """
    if not is_table_available(b.table_id, b.starts_at, b.ends_at):
        raise ValueError("Стол недоступен в выбранное время")
    sql = (
        "INSERT INTO bookings(user_id, table_id, starts_at, ends_at, guest_count, status, contact_name, contact_phone, notes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id"
    )
    with db.transaction() as tx:
        row = tx.fetchone(sql, b.to_insert_params())
        return _get_id(row)


def get_booking(booking_id: int) -> Booking | None:
    """
    Получает информацию о бронировании по ID.

    Args:
        booking_id: ID бронирования.

    Returns:
        Объект бронирования или None, если оно не найдено.
    """
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM bookings WHERE id=%s", [booking_id])
        return Booking.from_row(row) if row else None


def update_booking_times(booking_id: int, starts_at: datetime, ends_at: datetime, guest_count: int) -> int:
    """
    Обновляет время и количество гостей для бронирования.

    Args:
        booking_id: ID бронирования.
        starts_at: Новое время начала.
        ends_at: Новое время окончания.
        guest_count: Новое количество гостей.

    Returns:
        Количество обновленных записей.

    Raises:
        ValueError: Если стол недоступен в новое время.
    """
    bk = get_booking(booking_id)
    if not bk:
        return 0
    if not is_table_available(bk.table_id, starts_at, ends_at, booking_id_to_exclude=booking_id):
        raise ValueError("Стол недоступен в выбранное время")
    with db.transaction() as tx:
        return tx.execute(
            "UPDATE bookings SET starts_at=%s, ends_at=%s, guest_count=%s, updated_at=now() WHERE id=%s",
            [starts_at, ends_at, guest_count, booking_id],
        )


def set_booking_status(booking_id: int, status: str) -> int:
    """
    Устанавливает статус для бронирования.

    Args:
        booking_id: ID бронирования.
        status: Новый статус.

    Returns:
        Количество обновленных записей.
    """
    with db.transaction() as tx:
        return tx.execute("UPDATE bookings SET status=%s, updated_at=now() WHERE id=%s", [status, booking_id])


def cancel_booking(booking_id: int, reason: str | None = None) -> int:
    """
    Отменяет бронирование.

    Args:
        booking_id: ID бронирования.
        reason: Причина отмены (опционально).

    Returns:
        Количество обновленных записей.
    """
    with db.transaction() as tx:
        return tx.execute(
            "UPDATE bookings SET status='canceled', canceled_at=now(), cancel_reason=%s, updated_at=now() WHERE id=%s",
            [reason, booking_id],
        )


if __name__ == "__main__":
    create_tables()