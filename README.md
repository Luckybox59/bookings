# Приложение для бронирования столов

Простое GUI-приложение для управления пользователями, столами и бронированиями в ресторане.

## Запуск

1.  **Клонируйте репозиторий**

2.  **Создайте и активируйте виртуальное окружение**

    Для Windows:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

    Для macOS/Linux:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Установите зависимости**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте подключение к базе данных**

    Создайте файл `.env` в корне проекта, скопировав `.env.example`, и укажите свои данные для подключения к PostgreSQL.

    ```bash
    cp .env.example .env
    ```
    
    Затем отредактируйте `.env`:
    ```dotenv
    PG_HOST=localhost
    PG_PORT=5432
    PG_DB=your_database_name
    PG_USER=your_username
    PG_PASSWORD=your_password
    ```

5.  **Запустите приложение**

    При первом запуске приложение автоматически создаст необходимые таблицы в базе данных.

    ```bash
    python app.py
    ```


