import sqlite3
from sqlite3 import Connection
from config import *

def get_connection() -> Connection:
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица заявок
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, -- car или cargo
        number TEXT,
        upload_date TEXT,
        current_date TEXT,
        cities TEXT,
        type_car TEXT,
        manager_number TEXT,
        manager_name TEXT,
        manager_email TEXT,
        telegram_user_id INTEGER
    )
    """)

    # Таблица откликов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        responder_id INTEGER,
        responder_name TEXT,
        FOREIGN KEY(application_id) REFERENCES applications(id)
    )
    """)

    conn.commit()
    conn.close()

def init_db():
    """Инициализация базы данных, создание таблиц"""
    create_tables()

def add_application(data: dict, user_id: int, app_type: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO applications (type, number, upload_date, current_date, cities, type_car, 
                                  manager_number, manager_name, manager_email, telegram_user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        app_type,
        data.get('number'),
        data.get('upload_date'),
        data.get('current_date'),
        data.get('cities'),
        data.get('type_car'),
        data.get('manager_number'),
        data.get('manager_name'),
        data.get('manager_email'),
        user_id
    ))
    conn.commit()
    app_id = cursor.lastrowid
    conn.close()
    return app_id

def add_reply(application_id: int, responder_id: int, responder_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO replies (application_id, responder_id, responder_name)
        VALUES (?, ?, ?)
    """, (application_id, responder_id, responder_name))
    conn.commit()
    conn.close()

def get_application_data(app_id: int) -> dict:
    """Возвращает данные заявки по её id"""
    conn = sqlite3.connect(DB_NAME)  # Исправлено с DB_PATH на DB_NAME для согласованности
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {}

    # Пример: возвращаем словарь с полями заявки
    return {
        "id": row[0],
        "type": row[1],
        "number": row[2],
        "upload_date": row[3],
        "current_date": row[4],
        "cities": row[5],
        "type_car": row[6],
        "manager_number": row[7],
        "manager_name": row[8],
        "manager_email": row[9],
        "telegram_user_id": row[10],
    }