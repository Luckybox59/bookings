from __future__ import annotations
from dataclasses import dataclass, fields, is_dataclass
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence, get_args, get_origin

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, date, time
import typing as _t
import types  # <--- ДОБАВЬТЕ ЭТУ СТРОКУ


@dataclass(frozen=True)
class PGConfig:
    """Конфигурация подключения к PostgreSQL.

    Значения можно задать через .env или переменные окружения.

    Поля
    -----
    host: str
        Хост PostgreSQL (по умолчанию "localhost").
    port: int
        Порт PostgreSQL (по умолчанию 5432).
    dbname: str
        Имя базы данных (по умолчанию "postgres").
    user: str
        Имя пользователя (по умолчанию "postgres").
    password: str
        Пароль пользователя (по умолчанию пустой).
    sslmode: str | None
        Режим SSL (например, "require"), по умолчанию None.
    connect_timeout: int | None
        Таймаут подключения в секундах (по умолчанию 10).
    row_mode: str
        Режим возврата строк: "dict" (RealDictCursor) или "tuple".
    """
    host: str = "localhost"
    port: int = 5432
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = ""
    sslmode: str | None = None
    connect_timeout: int | None = 10
    row_mode: str = "dict"  # "dict" | "tuple"

    @staticmethod
    def from_env(prefix: str = "PG_") -> "PGConfig":
        """Загружает конфигурацию из .env/ENV с указанным префиксом.

        Поддерживаемые ключи: HOST, PORT, DB/DBNAME, USER, PASSWORD, SSLMODE,
        CONNECT_TIMEOUT, ROW_MODE.

        Параметры
        ---------
        prefix: str
            Префикс переменных окружения (по умолчанию "PG_").

        Возвращает
        -----------
        PGConfig
            Экземпляр конфигурации.
        """
        load_dotenv()

        def getenv(name: str, default: str | None = None) -> str | None:
            value = os.getenv(prefix + name)
            return value if value is not None else default

        return PGConfig(
            host=getenv("HOST", "localhost") or "localhost",
            port=int(getenv("PORT", "5432") or "5432"),
            dbname=getenv("DB", getenv("DBNAME", "postgres")) or "postgres",
            user=getenv("USER", "postgres") or "postgres",
            password=getenv("PASSWORD", "") or "",
            sslmode=getenv("SSLMODE", None),
            connect_timeout=int(getenv("CONNECT_TIMEOUT", "10") or "10"),
            row_mode=(getenv("ROW_MODE", "dict") or "dict").lower(),
        )


class _Connection:
    """Обертка соединения для простых операций.

    Предоставляет методы:
    - execute: DDL/DML запросы, возвращает число затронутых строк
    - fetchone: SELECT, возвращает одну строку или None
    - fetchall: SELECT, возвращает список строк

    Управление транзакциями выполняется на уровне драйвера.
    """

    def __init__(self, conn: psycopg2.extensions.connection, row_mode: str = "dict") -> None:
        self._conn = conn
        self._row_mode = row_mode

    def _cursor_factory(self):
        """Возвращает подходящий cursor_factory исходя из режима строк.

        Возвращает RealDictCursor для row_mode=="dict", иначе None (курсор по умолчанию).
        """
        return RealDictCursor if self._row_mode == "dict" else None

    def execute(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> int:
        """Выполняет DDL/DML запрос (INSERT/UPDATE/DELETE/DDL).

        Параметры
        ---------
        sql: str
            Текст SQL с плейсхолдерами %s.
        params: Sequence | Mapping | None
            Параметры запроса.

        Возвращает
        -----------
        int
            Число затронутых строк.
        """
        with self._conn.cursor(cursor_factory=self._cursor_factory()) as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def fetchone(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> Any | None:
        """Выполняет SELECT и возвращает одну строку.

        Формат строки зависит от row_mode: dict (RealDictCursor) или tuple.
        Возвращает None, если строк нет.
        """
        with self._conn.cursor(cursor_factory=self._cursor_factory()) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def fetchall(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> list[Any]:
        """Выполняет SELECT и возвращает все строки.

        Формат строк зависит от row_mode: dict (RealDictCursor) или tuple.
        """
        with self._conn.cursor(cursor_factory=self._cursor_factory()) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def close(self) -> None:
        """Закрывает соединение."""
        self._conn.close()

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class PGDriver:
    """Простой синхронный драйвер PostgreSQL на psycopg2.

    Предоставляет менеджеры контекста:
    - connect: одиночное подключение (autocommit=True)
    - transaction: транзакция (BEGIN/COMMIT/ROLLBACK)
    """

    def __init__(self, config: PGConfig) -> None:
        """Инициализирует драйвер с заданной конфигурацией."""
        self._cfg = config

    def _connect(self) -> psycopg2.extensions.connection:
        """Создает и возвращает низкоуровневое соединение psycopg2."""
        kwargs = {
            "host": self._cfg.host,
            "port": self._cfg.port,
            "dbname": self._cfg.dbname,
            "user": self._cfg.user,
            "password": self._cfg.password,
        }
        if self._cfg.sslmode:
            kwargs["sslmode"] = self._cfg.sslmode
        if self._cfg.connect_timeout:
            kwargs["connect_timeout"] = self._cfg.connect_timeout
        return psycopg2.connect(**kwargs)

    @contextmanager
    def connect(self) -> Iterator[_Connection]:
        """Менеджер контекста одиночного подключения.

        Включает autocommit, подходит для отдельных запросов без ручного управления транзакциями.
        """
        conn = self._connect()
        try:
            conn.autocommit = True
            yield _Connection(conn, row_mode=self._cfg.row_mode)
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[_Connection]:
        """Менеджер контекста транзакции.

        Отключает autocommit, при успешном завершении выполняет COMMIT,
        при исключении выполняет ROLLBACK.
        """
        conn = self._connect()
        try:
            conn.autocommit = False
            wrapper = _Connection(conn, row_mode=self._cfg.row_mode)
            yield wrapper
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_table(self, ddl_sql: str) -> None:
        """
        Выполняет один DDL-запрос (CREATE TABLE/INDEX/VIEW и т.п.).
        Работает в autocommit.
        """
        with self.connect() as conn:
            conn.execute(ddl_sql)

    def create_tables(self, ddl_list: list[str]) -> None:
        """
        Последовательно выполняет список DDL-запросов.
        Удобно для инициализации схемы.
        """
        with self.connect() as conn:
            for ddl in ddl_list:
                conn.execute(ddl)

    def ping(self) -> bool:
        """Проверяет доступность БД запросом SELECT 1.

        Возвращает True при успехе, иначе False.
        """
        try:
            with self.connect() as c:
                c.fetchone("SELECT 1;")
            return True
        except Exception:
            return False

    def ensure_model(self, model: type) -> None:
        """Создаёт таблицу по одной dataclass-модели, если её ещё нет."""
        ensure_schema(self, [model])

    def ensure_models(self, models: list[type]) -> None:
        """Создаёт таблицы по нескольким моделям, если их ещё нет."""
        ensure_schema(self, models)



# ====== Схема: генерация DDL по dataclass-моделям ======

_PY2SQL: dict[type, str] = {
    int: "INT",
    bool: "BOOLEAN",
    float: "DOUBLE PRECISION",
    str: "TEXT",
    bytes: "BYTEA",
    datetime: "TIMESTAMPTZ",
    date: "DATE",
    time: "TIME",
}


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    """Возвращает (базовый_тип, nullable?). Поддерживает Optional[T] / Union[T, None]."""
    origin = get_origin(tp)
    if origin is None:
        return tp, False
    # В Python 3.10+ `int | None` это types.UnionType, а не typing.Union
    if origin is _t.Union or origin is types.UnionType:
        args = [a for a in get_args(tp)]
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            return (non_none[0] if len(non_none) == 1 else non_none), True
    return tp, False


def _sql_type(py_type: Any) -> str:
    """Маппинг python-типов в базовый SQL-тип."""
    return _PY2SQL.get(py_type, "TEXT")


def build_create_table_ddl(model: type) -> str:
    """Строит простой CREATE TABLE IF NOT EXISTS по dataclass-модели.

    Требуются атрибуты у модели:
    - __table__: имя таблицы
    - __fkeys__: dict[field -> (ref_table, ref_column, on_delete)] (опционально)
    """
    if not is_dataclass(model):
        raise TypeError(f"{model} is not a dataclass")
    table = getattr(model, "__table__", None)
    if not table:
        raise ValueError(f"{model.__name__} has no __table__")
    fkeys: dict[str, tuple[str, str, str]] = getattr(model, "__fkeys__", {}) or {}

    # Резолвим аннотации типов (особенно при from __future__ import annotations)
    try:
        from typing import get_type_hints as _get_type_hints
        type_hints = _get_type_hints(model, include_extras=True)
    except Exception:
        type_hints = {}

    col_sql: list[str] = []
    extra_sql: list[str] = []  # CHECK/FOREIGN KEY

    for f in fields(model):
        name = f.name
        annotated = type_hints.get(name, f.type)
        base_type, nullable = _unwrap_optional(annotated)
        sql_t = _sql_type(base_type)

        # Первичный ключ для id
        if name == "id":
            col_sql.append("id SERIAL PRIMARY KEY")
            continue

        parts = [name, sql_t]
        # по требованию: NOT NULL только для id; остальные поля допускают NULL

        # Наиболее частые дефолты по именам полей
        if name in ("created_at", "updated_at") and sql_t in ("TIMESTAMPTZ",):
            parts.append("DEFAULT now()")

        col_sql.append(" ".join(parts))

        # Внешние ключи
        if name in fkeys:
            ref_table, ref_col, on_delete = fkeys[name]
            extra_sql.append(
                f"FOREIGN KEY ({name}) REFERENCES {ref_table}({ref_col}) ON DELETE {on_delete}"
            )

    all_parts = col_sql + extra_sql
    ddl = f"CREATE TABLE IF NOT EXISTS {table} (\n  " + ",\n  ".join(all_parts) + "\n);"
    return ddl


def _dict_get(row: Any, key: str) -> Any:
    """Безопасно получить значение из результата (dict или tuple)."""
    if isinstance(row, dict):
        return row.get(key)
    return row[0] if row else None


def table_exists(driver: "PGDriver", table: str) -> bool:
    """Проверяет существование таблицы в текущей схеме через to_regclass."""
    sql = "SELECT to_regclass(%s) IS NOT NULL AS exists"
    with driver.connect() as c:
        row = c.fetchone(sql, [table])
        val = _dict_get(row, "exists")
        return bool(val)


def ensure_schema(driver: "PGDriver", models: list[type]) -> None:
    """Создаёт отсутствующие таблицы на основе указанных моделей."""
    ddls: list[str] = []
    for m in models:
        table = getattr(m, "__table__", None)
        if not table:
            continue
        if not table_exists(driver, table):
            ddls.append(build_create_table_ddl(m))
    if ddls:
        driver.create_tables(ddls)

