import sqlite3

def setup_database():
    # Подключаемся к базе (файл tutor_bot.db создастся автоматически)
    conn = sqlite3.connect('../data/tutor_bot.db')
    cursor = conn.cursor()

    # Таблица учеников
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        telegram_id INTEGER PRIMARY KEY, -- ID ученика в Telegram
        name TEXT NOT NULL,
        balance INTEGER DEFAULT 0
    )
    ''')

    # Таблица уроков (расписание + домашка)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lessons (
        lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        lesson_datetime TEXT NOT NULL,    -- Время урока в формате 'YYYY-MM-DD HH:MM'
        status TEXT DEFAULT 'scheduled',  -- Статусы: 'scheduled' (запланирован), 'completed' (проведен), 'cancelled' (отменен)
        hw_status TEXT DEFAULT 'pending', -- Статусы ДЗ: 'pending' (ожидаем), 'done' (сделано)
        FOREIGN KEY (student_id) REFERENCES students (telegram_id)
    )
    ''')

    conn.commit()
    conn.close()
    print("База данных tutor_bot.db успешно создана!")

if __name__ == '__main__':
    setup_database()