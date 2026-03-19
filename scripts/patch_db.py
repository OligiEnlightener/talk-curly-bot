import sqlite3


def patch():
    conn = sqlite3.connect('../data/tutor_bot.db')
    cursor = conn.cursor()

    try:
        # Добавляем колонку hw_status со значением по умолчанию
        cursor.execute("ALTER TABLE students ADD COLUMN hw_status TEXT DEFAULT '⏳ Ждём'")
        conn.commit()
        print("Колонка hw_status успешно добавлена!")
    except sqlite3.OperationalError:
        print("Похоже, колонка уже существует или произошла ошибка.")
    finally:
        conn.close()


if __name__ == '__main__':
    patch()