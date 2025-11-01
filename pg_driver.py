"""
Драйвер для работы с PostgreSQL.

Этот модуль предоставляет классы для конфигурации, подключения и взаимодействия
с базой данных PostgreSQL, а также утилиты для автоматического создания таблиц
на основе dataclass моделей.
"""
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
import types


@dataclass(frozen=True)
class PGConfig:
    """
    Конфигурация для подключения к базе данных PostgreSQL.

    Attributes:
        host: Хост базы данных.
        port: Порт базы данных.
        dbname: Имя базы данных.
        user: Имя пользователя.
        password: Пароль.
        sslmode: Режим SSL.
        connect_timeout: Таймаут подключения.
        row_mode: Режим получения строк ('dict' или 'tuple').
    """
    host: str = "localhost"
    port: int = 5432
    dbname: str = "postgres"
    user: str = "postgres"
    password: str = ""
    sslmode: str | None = None
    connect_timeout: int | None = 10
    row_mode: str = "dict"

    @staticmethod
    def from_env(prefix: str = "PG_") -> "PGConfig":
        """
        Создает объект PGConfig из переменных окружения.

        Args:
            prefix: Префикс для имен переменных окружения.

        Returns:
            Экземпляр PGConfig.
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
    """
    Обертка над соединением psycopg2 для упрощения выполнения запросов.
    Не предназначена для прямого использования.
    """
    def __init__(self, conn: psycopg2.extensions.connection, row_mode: str = "dict") -> None:
        self._conn = conn
        self._row_mode = row_mode

    def _cursor_factory(self):
        """Возвращает фабрику курсора в зависимости от row_mode."""
        return RealDictCursor if self._row_mode == "dict" else None

    def execute(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> int:
        """
        Выполняет SQL-запрос.

        Args:
            sql: Текст SQL-запроса.
            params: Параметры для запроса.

        Returns:
            Количество затронутых строк.
        """
        with self._conn.cursor(cursor_factory=self._cursor_factory()) as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def fetchone(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> Any | None:
        """
        Выполняет SQL-запрос и возвращает одну строку результата.

        Args:
            sql: Текст SQL-запроса.
            params: Параметры для запроса.

        Returns:
            Одна строка результата или None.
        """
        with self._conn.cursor(cursor_factory=self._cursor_factory()) as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def fetchall(self, sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None) -> list[Any]:
        """
        Выполняет SQL-запрос и возвращает все строки результата.

        Args:
            sql: Текст SQL-запроса.
            params: Параметры для запроса.

        Returns:
            Список всех строк результата.
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
    """
    Основной класс драйвера для работы с PostgreSQL.
    """
    def __init__(self, config: PGConfig) -> None:
        self._cfg = config

    def _connect(self) -> psycopg2.extensions.connection:
        """Устанавливает новое соединение с базой данных."""
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
        """
        Предоставляет контекстный менеджер для одного соединения с автокоммитом.

        Yields:
            Объект _Connection.
        """
        conn = self._connect()
        try:
            conn.autocommit = True
            yield _Connection(conn, row_mode=self._cfg.row_mode)
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[_Connection]:
        """
        Предоставляет контекстный менеджер для транзакции.
        Коммитит при успешном выходе, откатывает при исключении.

        Yields:
            Объект _Connection.
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
        Создает одну таблицу, выполняя DDL-запрос.

        Args:
            ddl_sql: SQL-запрос для создания таблицы.
        """
        with self.connect() as conn:
            conn.execute(ddl_sql)

    def create_tables(self, ddl_list: list[str]) -> None:
        """
        Создает несколько таблиц, выполняя список DDL-запросов.

        Args:
            ddl_list: Список SQL-запросов для создания таблиц.
        """
        with self.connect() as conn:
            for ddl in ddl_list:
                conn.execute(ddl)

    def ping(self) -> bool:
        """
        Проверяет соединение с базой данных.

        Returns:
            True, если соединение успешно, иначе False.
        """
        try:
            with self.connect() as c:
                c.fetchone("SELECT 1;")
            return True
        except Exception:
            return False

    def ensure_model(self, model: type) -> None:
        """
        Гарантирует, что для указанной модели существует таблица в БД.

        Args:
            model: Класс-модель (dataclass).
        """
        ensure_schema(self, [model])

    def ensure_models(self, models: list[type]) -> None:
        """
        Гарантирует, что для всех указанных моделей существуют таблицы в БД.

        Args:
            models: Список классов-моделей (dataclass).
        """
        ensure_schema(self, models)


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
    """
    "Разворачивает" опциональный тип (Union[T, None]) и возвращает базовый тип.

    Args:
        tp: Тип для проверки.

    Returns:
        Кортеж (базовый тип, является ли он опциональным).
    """
    origin = get_origin(tp)
    if origin is None:
        return tp, False
    if origin is _t.Union or origin is types.UnionType:
        args = [a for a in get_args(tp)]
        if type(None) in args:
            non_none = [a for a in args if a is not type(None)]
            return (non_none[0] if len(non_none) == 1 else non_none), True
    return tp, False


def _sql_type(py_type: Any) -> str:
    """
    Сопоставляет тип Python с типом SQL.

    Args:
        py_type: Тип Python.

    Returns:
        Строка с названием типа SQL.
    """
    return _PY2SQL.get(py_type, "TEXT")


def build_create_table_ddl(model: type) -> str:
    """
    Строит SQL DDL для создания таблицы на основе dataclass-модели.

    Args:
        model: Класс-модель (dataclass).

    Returns:
        Строка с SQL-запросом CREATE TABLE.

    Raises:
        TypeError: Если модель не является dataclass.
        ValueError: Если у модели не определен атрибут __table__.
    """
    if not is_dataclass(model):
        raise TypeError(f"{model} is not a dataclass")
    table = getattr(model, "__table__", None)
    if not table:
        raise ValueError(f"{model.__name__} has no __table__")
    fkeys: dict[str, tuple[str, str, str]] = getattr(model, "__fkeys__", {}) or {}

    try:
        from typing import get_type_hints as _get_type_hints
        type_hints = _get_type_hints(model, include_extras=True)
    except Exception:
        type_hints = {}

    col_sql: list[str] = []
    extra_sql: list[str] = []

    for f in fields(model):
        name = f.name
        annotated = type_hints.get(name, f.type)
        base_type, nullable = _unwrap_optional(annotated)
        sql_t = _sql_type(base_type)

        if name == "id":
            col_sql.append("id SERIAL PRIMARY KEY")
            continue

        parts = [name, sql_t]

        if name in ("created_at", "updated_at") and sql_t in ("TIMESTAMPTZ",):
            parts.append("DEFAULT now()")

        col_sql.append(" ".join(parts))

        if name in fkeys:
            ref_table, ref_col, on_delete = fkeys[name]
            extra_sql.append(
                f"FOREIGN KEY ({name}) REFERENCES {ref_table}({ref_col}) ON DELETE {on_delete}"
            )

    all_parts = col_sql + extra_sql
    ddl = f"CREATE TABLE IF NOT EXISTS {table} (\n  " + ",\n  ".join(all_parts) + "\n);"
    return ddl


def _dict_get(row: Any, key: str) -> Any:
    """
    Безопасно извлекает значение из строки результата (словаря или кортежа).

    Args:
        row: Строка результата.
        key: Ключ (для словаря).

    Returns:
        Значение.
    """
    if isinstance(row, dict):
        return row.get(key)
    return row[0] if row else None


def table_exists(driver: "PGDriver", table: str) -> bool:
    """
    Проверяет, существует ли таблица в базе данных.

    Args:
        driver: Экземпляр PGDriver.
        table: Имя таблицы.

    Returns:
        True, если таблица существует, иначе False.
    """
    sql = "SELECT to_regclass(%s) IS NOT NULL AS exists"
    with driver.connect() as c:
        row = c.fetchone(sql, [table])
        val = _dict_get(row, "exists")
        return bool(val)


def ensure_schema(driver: "PGDriver", models: list[type]) -> None:
    """
    Проверяет существование таблиц для моделей и создает их при необходимости.

    Args:
        driver: Экземпляр PGDriver.
        models: Список классов-моделей.
    """
    ddls: list[str] = []
    for m in models:
        table = getattr(m, "__table__", None)
        if not table:
            continue
        if not table_exists(driver, table):
            ddls.append(build_create_table_ddl(m))
    if ddls:
        driver.create_tables(ddls)

