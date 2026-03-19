import sqlite3


def add_students():
    conn = sqlite3.connect('../data/tutor_bot.db')
    cursor = conn.cursor()

    # Данные студентов: (telegram_id, имя, текущий баланс)
    # Замените 12345678, 87654321, 11223344 на реальные ID, если хотите протестировать на себе
    test_students = [
        (12345678, 'Алексей', 4),
        (87654321, 'Мария', 2),
        (11223344, 'Иван', 1)
    ]

    try:
        cursor.executemany('''
                           INSERT INTO students (telegram_id, name, balance)
                           VALUES (?, ?, ?)
                           ''', test_students)
        conn.commit()
        print("Тестовые студенты успешно добавлены!")
    except sqlite3.IntegrityError:
        print("Ошибка: Студенты с такими ID уже существуют в базе.")

    conn.close()


if __name__ == '__main__':
    add_students()