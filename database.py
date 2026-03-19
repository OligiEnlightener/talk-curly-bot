import sqlite3
import json
from datetime import datetime, timedelta

from config import PATH_TO_OBSIDIAN_JSON, DB_PATH


def update_obsidian_json():
    try:
        # 1. Подключаемся ТОЛЬКО к файлу .db
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Это поможет сделать красивый список
            cursor = conn.cursor()
            cursor.execute("SELECT name, balance, hw_status FROM students")
            rows = cursor.fetchall()

            # Превращаем результат в список словарей
            data = [dict(row) for row in rows]

        # 2. Записываем данные в JSON-файл
        with open(PATH_TO_OBSIDIAN_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("Данные для Obsidian успешно обновлены!")

    except sqlite3.DatabaseError as e:
        print(f"Ошибка: проверьте, что DB_PATH указывает на .db файл! {e}")

def get_all_students():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, balance FROM students")
    return cursor.fetchall()

def get_student_by_id(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance FROM students WHERE telegram_id = ?", (user_id,))
        return cursor.fetchone() # Добавили возврат результата

def update_hw_status(user_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET hw_status = ? WHERE telegram_id = ?", (status, user_id))
        conn.commit() # Не забываем коммит!

def get_lessons_by_date(date_str):
    """Получаем все уроки на конкретную дату для админа"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Соединяем с таблицей студентов, чтобы получить имя
        cursor.execute('''
            SELECT s.name, l.lesson_time, s.hw_status 
            FROM lessons l
            JOIN students s ON l.student_id = s.telegram_id 
            WHERE l.lesson_time LIKE ?
        ''', (f"{date_str}%",))
        return cursor.fetchall()


def update_student_balance(user_id):
    # Используем 'with', чтобы соединение закрылось само
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 1. Сначала проверяем текущий баланс и имя
        cursor.execute("SELECT balance, name FROM students WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()

        if not result:
            return None, None

        current_balance, name = result

        if current_balance > 0:
            new_balance = current_balance - 1
            # !!! КРИТИЧЕСКИ ВАЖНО: Обновляем запись в базе !!!
            cursor.execute("UPDATE students SET balance = ? WHERE telegram_id = ?", (new_balance, user_id))
            conn.commit()  # Сохраняем изменения в файле .db
            return new_balance, name
        else:
            return 0, name


def get_emoji_number(n):
    emoji_map = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
                 '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
    return ''.join(emoji_map[digit] for digit in str(n))


def get_schedule(period, user_id=None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        now = datetime.now()

        if period == 'day':
            end_date = now.replace(hour=23, minute=59)
        elif period == 'week':
            end_date = now + timedelta(days=7)
        else:
            end_date = now + timedelta(days=30)

        start_str = now.strftime('%Y-%m-%d %H:%M')
        end_str = end_date.strftime('%Y-%m-%d %H:%M')

        # Используем названия из вашей реальной таблицы: student_id и lesson_time
        # Добавляем JOIN, чтобы достать имя студента, так как в lessons только ID
        query = """
            SELECT l.lesson_time, s.name 
            FROM lessons l
            JOIN students s ON l.student_id = s.telegram_id
            WHERE l.lesson_time BETWEEN ? AND ? 
            AND l.status != 'cancelled'
        """
        params = [start_str, end_str]

        if user_id:
            query += " AND l.student_id = ?"
            params.append(user_id)

        query += " ORDER BY l.lesson_time ASC"
        cursor.execute(query, params)
        return cursor.fetchall()