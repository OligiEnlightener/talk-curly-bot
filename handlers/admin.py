import asyncio
import sqlite3
from datetime import datetime
from aiogram import F, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID, DB_PATH
from database import update_obsidian_json, get_emoji_number, update_student_balance, get_lessons_by_date
from states import ScheduleLesson, RegisterStudent
from utils.calendar_grid import generate_calendar
from utils.scheduler import add_lesson, get_finished_lessons

router = Router()

# Фильтр: только для админа
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)


# --- 1. РАСПИСАНИЕ (КАЛЕНДАРЬ) ---

@router.message(F.text == "📚 Расписание")
async def show_admin_calendar(message: types.Message):
    # Отправляем именно сетку (как на фото)
    await message.answer("Ваш календарь занятий:", reply_markup=generate_calendar())


@router.callback_query(F.data.startswith("calendar_move_"))
async def admin_calendar_nav(callback: types.CallbackQuery):
    _, _, year, month = callback.data.split("_")
    await callback.message.edit_reply_markup(
        reply_markup=generate_calendar(int(year), int(month))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calendar_day_"))
async def admin_day_details(callback: types.CallbackQuery):
    _, _, year, month, day = callback.data.split("_")
    # Формируем дату для поиска в БД
    date_str = f"{year}-{int(month):02d}-{int(day):02d}"

    # Важно: используем вашу функцию из database.py
    lessons = get_lessons_by_date(date_str)

    if not lessons:
        await callback.answer(f"На {day}.{month} уроков нет", show_alert=True)
    else:
        text = f"📅 Занятия на {day}.{month}:\n"
        for name, time, hw in lessons:
            time_only = time.split(' ')[1]
            text += f"• {time_only} — {name}\n"

        # Показываем список уроков во всплывающем окне
        await callback.answer(text, show_alert=True)


# --- 2. СПИСАНИЕ УРОКОВ (ФИНАЛ) ---

@router.callback_query(F.data.startswith("done_"))
async def confirm_lesson_done(callback: types.CallbackQuery):
    data = callback.data.split("_")
    l_id, s_tg_id = data[1], int(data[2])

    new_bal, name = update_student_balance(s_tg_id)

    if name:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE lessons SET status = 'confirmed' WHERE id = ?", (l_id,))
            conn.commit()

        update_obsidian_json()
        await callback.message.edit_text(f"✅ Урок с **{name}** списан. Остаток: {new_bal}")
    else:
        await callback.answer("Ошибка: студент не найден.")
    await callback.answer()


@router.callback_query(F.data.startswith("skip_"))
async def cancel_lesson_done(callback: types.CallbackQuery):
    l_id = callback.data.split("_")[1]
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE lessons SET status = 'cancelled' WHERE id = ?", (l_id,))
        conn.commit()
    await callback.message.edit_text("❌ Списание отменено.")
    await callback.answer()


# --- 3. ПЛАНИРОВАНИЕ ---

@router.message(F.text == "📅 Запланировать")
async def plan_lesson_start(message: types.Message, state: FSMContext):
    await message.answer("Для какого студента планируем урок? (Введите имя)")
    await state.set_state(ScheduleLesson.waiting_for_name)


@router.message(ScheduleLesson.waiting_for_name)
async def plan_lesson_name(message: types.Message, state: FSMContext):
    await state.update_data(student_name=message.text)
    await message.answer(f"Студент: **{message.text}**\nВведите время: `ГГГГ-ММ-ДД ЧЧ:ММ`", parse_mode="Markdown")
    await state.set_state(ScheduleLesson.waiting_for_datetime)


@router.message(ScheduleLesson.waiting_for_datetime)
async def plan_lesson_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        datetime.strptime(message.text, '%Y-%m-%d %H:%M')
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT telegram_id FROM students WHERE name = ?", (data['student_name'],))
            res = cursor.fetchone()

        if res:
            add_lesson(res[0], message.text)
            await message.answer(f"✅ Записано на {message.text}")
            await state.clear()
        else:
            await message.answer("❌ Студент не найден в базе.")
    except ValueError:
        await message.answer("❌ Ошибка формата! Пример: 2026-03-20 15:00")


# --- 4. ВСПОМОГАТЕЛЬНОЕ ---

@router.message(F.text == "👥 Список студентов")
async def admin_show_students(message: types.Message):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance, hw_status FROM students")
        rows = cursor.fetchall()

    if not rows:
        await message.answer("Учеников пока нет.")
        return

    res = "📋 Студенты:\n\n👤 Имя | 📚 Бал. | 📝 ДЗ\n" + "-" * 20 + "\n"
    for n, b, s in rows:
        icon = "✅" if "Готово" in s else "⏳"
        res += f"{n} | {get_emoji_number(b)} | {icon}\n"
    await message.answer(res, parse_mode="Markdown")


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()


async def check_lessons_loop(bot):
    while True:
        try:
            finished = get_finished_lessons()
            for l_id, name, tg_id in finished:
                builder = InlineKeyboardBuilder()
                builder.button(text="✅ Списать", callback_data=f"done_{l_id}_{tg_id}")
                builder.button(text="❌ Отмена", callback_data=f"skip_{l_id}")
                await bot.send_message(ADMIN_ID, f"⏰ Урок с **{name}** завершен. Списываем?",
                                       reply_markup=builder.as_markup(), parse_mode="Markdown")
        except Exception as e:
            print(f"Ошибка цикла: {e}")
        await asyncio.sleep(60)