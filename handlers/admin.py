import asyncio
import sqlite3
from datetime import datetime
from aiogram import F, types, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID, DB_PATH
from database import update_obsidian_json, get_emoji_number, update_student_balance, get_lessons_by_date
from states import ScheduleLesson, RegisterStudent
from utils.calendar_grid import generate_calendar, generate_time_grid
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


@router.callback_query(F.data.startswith("calendar_day_"), StateFilter(None))
async def admin_day_details(callback: types.CallbackQuery):
    _, _, year, month, day = callback.data.split("_")
    date_str = f"{year}-{int(month):02d}-{int(day):02d}"
    lessons = get_lessons_by_date(date_str)

    if not lessons:
        await callback.answer(f"На {day}.{month} уроков нет", show_alert=True)
    else:
        # Вместо Alert отправляем сообщение с кнопками управления
        builder = InlineKeyboardBuilder()
        text = f"📅 Уроки {day}.{month}:\n"

        for name, time, hw in lessons:
            time_only = time.split(' ')[1]
            # Получаем ID урока из БД (нужно добавить его в SELECT в database.py)
            # Предположим, вы обновили get_lessons_by_date, чтобы она возвращала и ID
            # builder.button(text=f"🗑 {time_only} {name}", callback_data=f"delete_les_{lesson_id}")
            text += f"• {time_only} — {name}\n"

        await callback.message.answer(text, reply_markup=builder.as_markup())
        await callback.answer()


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
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, name FROM students")
        students = cursor.fetchall()

    if not students:
        await message.answer("Сначала добавьте студентов!")
        return

    builder = InlineKeyboardBuilder()
    for tg_id, name in students:
        builder.button(text=name, callback_data=f"plan_st_{tg_id}")
    builder.adjust(2)

    await message.answer("Выберите студента:", reply_markup=builder.as_markup())
    await state.set_state(ScheduleLesson.waiting_for_student)


@router.callback_query(F.data.startswith("plan_st_"))
async def plan_student_chosen(callback: types.CallbackQuery, state: FSMContext):
    student_id = callback.data.split("_")[2]
    await state.update_data(chosen_student_id=student_id)

    # Вместо списка студентов присылаем календарь
    await callback.message.edit_text(
        "Выберите дату занятия:",
        reply_markup=generate_calendar()  # Используем ваш существующий генератор
    )
    await state.set_state(ScheduleLesson.waiting_for_date)


@router.callback_query(ScheduleLesson.waiting_for_date, F.data.startswith("calendar_day_"))
async def plan_date_chosen(callback: types.CallbackQuery, state: FSMContext):
    _, _, year, month, day = callback.data.split("_")
    date_str = f"{year}-{int(month):02d}-{int(day):02d}"

    data = await state.get_data()
    student_id = data['chosen_student_id']

    await state.update_data(chosen_date=date_str)

    # Вместо календаря открываем часы
    await callback.message.edit_text(
        f"Выбрана дата: {day}.{month}.{year}\nВыберите время начала:",
        reply_markup=generate_time_grid(student_id, date_str)
    )
    await state.set_state(ScheduleLesson.waiting_for_time)


@router.callback_query(F.data.startswith("set_time_"))
async def plan_final_save(callback: types.CallbackQuery, state: FSMContext):
    _, _, student_id, date_str, time_val = callback.data.split("_")
    full_datetime = f"{date_str} {time_val}"

    add_lesson(int(student_id), full_datetime)  # Ваша функция из scheduler.py
    update_obsidian_json()  #

    await callback.message.edit_text(f"✅ Урок успешно запланирован на {full_datetime}")
    await state.clear()

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