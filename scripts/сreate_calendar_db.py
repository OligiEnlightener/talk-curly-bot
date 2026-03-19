import sqlite3
import os

# Определяем путь к базе
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, 'data', 'tutor_bot.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Удаляем старую таблицу, если она была создана неправильно
cursor.execute("DROP TABLE IF EXISTS lessons")

# 2. Создаем таблицу заново с ПРАВИЛЬНЫМИ колонками
cursor.execute('''
    CREATE TABLE lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        lesson_time DATETIME,
        status TEXT DEFAULT 'planned'
    )
''')

conn.commit()
conn.close()
print("Таблица lessons успешно пересоздана!")