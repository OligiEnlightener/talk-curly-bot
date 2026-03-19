import sqlite3
from datetime import datetime

from utils.calendar_grid import DB_PATH


def add_lesson(student_id, date_str):
    """date_str в формате 'YYYY-MM-DD HH:MM'"""
    conn = sqlite3.connect('data/tutor_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO lessons (student_id, lesson_time) VALUES (?, ?)",
                   (student_id, date_str))
    conn.commit()
    conn.close()


def get_finished_lessons():
    """Ищем уроки, которые должны были закончиться (например, час назад)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Находим уроки, время которых прошло, но они еще не списаны
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor.execute('''
                   SELECT lessons.id, students.name, students.telegram_id
                   FROM lessons
                            JOIN students ON lessons.student_id = students.telegram_id
                   WHERE lessons.lesson_time <= ?
                     AND lessons.status = 'planned'
                   ''', (now,))

    lessons = cursor.fetchall()
    conn.close()
    return lessons  # Возвращает список (id_урока, имя_ученика, tg_id)