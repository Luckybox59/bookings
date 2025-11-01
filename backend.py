from pg_driver import PGConfig, PGDriver
from models.users import User
from models.tables import Table
from models.booking import Booking
from datetime import datetime
from typing import Any

# Инициализация драйвера один раз
db = PGDriver(PGConfig.from_env())


# ===== Схема =====
def create_tables():
    db.ensure_models([User, Table, Booking])


# ===== Утилиты =====
def _get_id(row: Any) -> int:
    return int(row[0] if not isinstance(row, dict) else row["id"]) if row is not None else 0


# ===== Users CRUD =====
def create_user(u: User) -> int:
    sql = "INSERT INTO users(email, full_name, phone) VALUES (%s,%s,%s) RETURNING id"
    with db.transaction() as tx:
        row = tx.fetchone(sql, u.to_insert_params())
        return _get_id(row)


def get_user_by_id(user_id: int) -> User | None:
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM users WHERE id=%s", [user_id])
        return User.from_row(row) if row else None


def update_user(u: User) -> int:
    sql = "UPDATE users SET email=%s, full_name=%s, phone=%s, updated_at=now() WHERE id=%s"
    with db.transaction() as tx:
        return tx.execute(sql, u.to_update_params())


def delete_user(user_id: int) -> int:
    with db.transaction() as tx:
        return tx.execute("DELETE FROM users WHERE id=%s", [user_id])


# ===== Tables CRUD =====
def create_table_rec(t: Table) -> int:
    sql = (
        "INSERT INTO tables(number,capacity,zone,status,notes) "
        "VALUES (%s,%s,%s,%s,%s) RETURNING id"
    )
    with db.transaction() as tx:
        row = tx.fetchone(sql, t.to_insert_params())
        return _get_id(row)


def get_table(table_id: int) -> Table | None:
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM tables WHERE id=%s", [table_id])
        return Table.from_row(row) if row else None


def update_table_rec(t: Table) -> int:
    sql = (
        "UPDATE tables SET number=%s,capacity=%s,zone=%s,status=%s,notes=%s, updated_at=now() WHERE id=%s"
    )
    with db.transaction() as tx:
        return tx.execute(sql, t.to_update_params())


def delete_table(table_id: int) -> int:
    with db.transaction() as tx:
        return tx.execute("DELETE FROM tables WHERE id=%s", [table_id])


# ===== Bookings CRUD =====
def is_table_available(table_id: int, starts_at: datetime, ends_at: datetime, booking_id_to_exclude: int | None = None) -> bool:
    """Проверка пересечения активных бронирований по интервалу времени."""
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
    with db.connect() as conn:
        row = conn.fetchone("SELECT * FROM bookings WHERE id=%s", [booking_id])
        return Booking.from_row(row) if row else None


def update_booking_times(booking_id: int, starts_at: datetime, ends_at: datetime, guest_count: int) -> int:
    # Узнаём стол бронирования
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
    with db.transaction() as tx:
        return tx.execute("UPDATE bookings SET status=%s, updated_at=now() WHERE id=%s", [status, booking_id])


def cancel_booking(booking_id: int, reason: str | None = None) -> int:
    with db.transaction() as tx:
        return tx.execute(
            "UPDATE bookings SET status='canceled', canceled_at=now(), cancel_reason=%s, updated_at=now() WHERE id=%s",
            [reason, booking_id],
        )




































if __name__ == "__main__":
    create_tables()