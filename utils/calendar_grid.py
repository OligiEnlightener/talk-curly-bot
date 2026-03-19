import calendar
from datetime import datetime, timedelta
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tutor_bot.db')


def get_days_with_lessons(year, month):
    """Получает список дней месяца, на которые назначены уроки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Ищем все уроки в конкретном месяце
    start_date = f"{year}-{month:02d}-01"
    end_date = f"{year}-{month:02d}-31"

    cursor.execute("SELECT lesson_time FROM lessons WHERE lesson_time BETWEEN ? AND ?", (start_date, end_date))
    dates = cursor.fetchall()
    conn.close()

    # Извлекаем только день (число) из строки даты
    return [int(d[0].split('-')[2].split(' ')[0]) for d in dates]


def generate_calendar(year=None, month=None):
    if year is None: year = datetime.now().year
    if month is None: month = datetime.now().month

    builder = InlineKeyboardBuilder()

    # Заголовок: Месяц и Год
    month_name = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"][month - 1]
    builder.row(InlineKeyboardButton(text=f"📅 {month_name} {year}", callback_data="ignore"))

    # Дни недели
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="ignore") for d in days_of_week])

    # Получаем дни с уроками
    lessons_days = get_days_with_lessons(year, month)

    # Сетка календаря
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        buttons = []
        for day in week:
            if day == 0:
                buttons.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                # Если в этот день есть урок, добавляем маркер
                text = f"•{day}" if day in lessons_days else str(day)
                buttons.append(InlineKeyboardButton(text=text, callback_data=f"calendar_day_{year}_{month}_{day}"))
        builder.row(*buttons)

    # Кнопки навигации (Пред. / След. месяц)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    builder.row(
        InlineKeyboardButton(text="⬅️", callback_data=f"calendar_move_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text="➡️", callback_data=f"calendar_move_{next_year}_{next_month}")
    )

    return builder.as_markup()

def get_student_week_grid(student_id):
    builder = InlineKeyboardBuilder()

    # Определяем начало текущей недели (Понедельник)
    now = datetime.now()
    start_of_week = now - timedelta(days=now.weekday())

    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    # Заголовок с периодом недели
    end_of_week = start_of_week + timedelta(days=6)
    period = f"📅 {start_of_week.strftime('%d.%m')} - {end_of_week.strftime('%d.%m')}"
    builder.row(InlineKeyboardButton(text=period, callback_data="ignore"))

    # Подключаемся к БД, чтобы пометить дни с уроками
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    buttons = []
    for i in range(7):
        current_day = start_of_week + timedelta(days=i)
        day_str = current_day.strftime('%Y-%m-%d')

        # Проверяем, есть ли урок у ЭТОГО студента в ЭТОТ день
        cursor.execute("SELECT id FROM lessons WHERE student_id = ? AND lesson_time LIKE ?",
                       (student_id, f"{day_str}%"))
        has_lesson = cursor.fetchone()

        # Формируем текст кнопки: "Пн 18" или "📚 Пн 18"
        label = f"{days_ru[i]} {current_day.day}"
        if has_lesson:
            label = f"🔴 {label}"

        buttons.append(InlineKeyboardButton(
            text=label,
            callback_data=f"std_day_{day_str}"
        ))

    conn.close()

    # Размещаем кнопки (например, 4 в первом ряду, 3 во втором или все в один ряд)
    builder.row(*buttons[:4])
    builder.row(*buttons[4:])

    return builder.as_markup()

def generate_time_grid(student_id, date_str):
    builder = InlineKeyboardBuilder()
    # Генерируем часы с 08:00 до 22:00
    for hour in range(8, 23):
        time_val = f"{hour:02d}:00"
        # callback содержит ID студента, дату и выбранное время
        builder.button(
            text=time_val,
            callback_data=f"set_time_{student_id}_{date_str}_{time_val}"
        )
    builder.adjust(4) # По 4 кнопки в ряд
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_planning"))
    return builder.as_markup()