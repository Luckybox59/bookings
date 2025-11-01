## Простой драйвер PostgreSQL (psycopg2 + dotenv)

Минимальный независимый sync-драйвер для PostgreSQL. Поддерживает:

- Подключение из `.env`/ENV через `PG_`-префикс
- Запросы: `execute`, `fetchone`, `fetchall`
- Транзакции через контекст-менеджер
- Режим строк: `dict` (RealDictCursor) или `tuple`
- `ping()` для проверки доступности БД

### Установка

```bash
pip install psycopg2-binary python-dotenv
```

### Переменные окружения (.env)

```dotenv
PG_HOST=localhost
PG_PORT=5432
PG_DB=postgres
PG_USER=postgres
PG_PASSWORD=postgres
PG_SSLMODE=disable
PG_CONNECT_TIMEOUT=10
PG_ROW_MODE=dict
```

Поддерживаются также переменные без `.env` — напрямую из окружения.

### Быстрый старт

```python
from pg_driver import PGConfig, PGDriver

cfg = PGConfig.from_env()  # или PGConfig(host="...", dbname="...", user="...", password="...")
db = PGDriver(cfg)

# Пинг
print("db up?", db.ping())

# Одиночное подключение (autocommit)
with db.connect() as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS t (id SERIAL PRIMARY KEY, name TEXT)")
    print(conn.fetchone("SELECT 1 AS ok"))  # {'ok': 1} при PG_ROW_MODE=dict

# Транзакция
try:
    with db.transaction() as tx:
        tx.execute("INSERT INTO t(name) VALUES(%s)", ["alice"])
        tx.execute("INSERT INTO t(name) VALUES(%s)", ["bob"])
        rows = tx.fetchall("SELECT id, name FROM t ORDER BY id")
        print(rows)
except Exception as e:
    print("tx failed:", e)
```

### API кратко

- `PGConfig.from_env(prefix: str = "PG_") -> PGConfig`
- `PGDriver(config: PGConfig)`
- `PGDriver.connect() -> contextmanager[_Connection]` — autocommit
- `PGDriver.transaction() -> contextmanager[_Connection]` — tx (BEGIN/COMMIT/ROLLBACK)
- `_Connection.execute(sql, params=None) -> int`
- `_Connection.fetchone(sql, params=None) -> dict|tuple|None`
- `_Connection.fetchall(sql, params=None) -> list[dict|tuple]`
- `PGDriver.ping() -> bool`

### Заметки

- Плейсхолдеры параметров — `%s` (особенность psycopg2).
- Для словарей результатов используйте `PG_ROW_MODE=dict` (по умолчанию).


