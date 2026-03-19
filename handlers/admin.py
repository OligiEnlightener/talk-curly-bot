import asyncio
import sqlite3
from datetime import datetime
from aiogram import F, types, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.common import show_day_actions, resched_start, resched_date_chosen, resched_final


from config import ADMIN_ID, DB_PATH
from database import update_obsidian_json, get_emoji_number, update_student_balance, get_lessons_by_date, \
    get_student_by_id, get_student_monthly_lessons
from states import ScheduleLesson, RegisterStudent, RescheduleState
from utils.calendar_grid import generate_calendar, generate_time_grid
from utils.scheduler import add_lesson, get_finished_lessons

router = Router()

# Фильтр: только для админа
router.message.filter(F.from_user.id == ADMIN_ID)
router.callback_query.filter(F.from_user.id == ADMIN_ID)


# --- 1. РАСПИСАНИЕ (КАЛЕНДАРЬ) ---
@router.callback_query(F.data.startswith("st_name_"))
async def show_student_lessons(callback: types.CallbackQuery):
    student_id = int(callback.data.split("_")[2])

    # Получаем имя студента для заголовка
    student_info = get_student_by_id(student_id)
    student_name = student_info[0] if student_info else "Ученик"

    lessons = get_student_monthly_lessons(student_id)

    if not lessons:
        await callback.answer(f"У {student_name} нет уроков в этом месяце", show_alert=True)
        return

    builder = InlineKeyboardBuilder()

    for lesson_time, lesson_id in lessons:
        # Превращаем "2026-03-19 13:00" в "19.03 | 13:00"
        dt = datetime.strptime(lesson_time, '%Y-%m-%d %H:%M')
        btn_text = dt.strftime('%d.%m | %H:%M')

        # При нажатии на конкретный урок можно открыть меню переноса (из common.py)
        builder.button(text=btn_text, callback_data=f"resched_start_{lesson_id}")

    builder.adjust(2)  # Кнопки в два ряда
    builder.row(InlineKeyboardButton(text="⬅️ К списку студентов", callback_data="back_to_students"))

    await callback.message.edit_text(
        f"📅 Уроки **{student_name}** на этот месяц:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


# Кнопка возврата
@router.callback_query(F.data == "back_to_students")
async def back_to_students_list(callback: types.CallbackQuery):
    await admin_show_students(callback.message)  # Вызываем вашу существующую функцию
    await callback.answer()
@router.message(F.text == "📚 Расписание")
async def show_admin_calendar(message: types.Message):
    await message.answer("Ваш календарь занятий:", reply_markup=generate_calendar())

@router.callback_query(F.data.startswith("calendar_move_"))
async def admin_calendar_nav(callback: types.CallbackQuery):
    _, _, year, month = callback.data.split("_")
    await callback.message.edit_reply_markup(
        reply_markup=generate_calendar(int(year), int(month))
    )
    await callback.answer()

@router.callback_query(F.data.startswith("calendar_day_"), StateFilter(None))

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
        cursor.execute("SELECT name, balance, hw_status, telegram_id FROM students")
        rows = cursor.fetchall()

    if not rows:
        await message.answer("Учеников пока нет.")
        return

    builder = InlineKeyboardBuilder()

    # --- ШАПКА ТАБЛИЦЫ ---
    # Добавляем 3 кнопки заголовка
    builder.add(InlineKeyboardButton(text="👤 Имя", callback_data="ignore"))
    builder.add(InlineKeyboardButton(text="📚 Баллы", callback_data="ignore"))
    builder.add(InlineKeyboardButton(text="📝 ДЗ", callback_data="ignore"))

    # --- СТРОКИ СО СТУДЕНТАМИ ---
    for name, balance, hw_status, tg_id in rows:
        hw_icon = "✅" if "Готово" in hw_status else "⏳"

        # 1. Кнопка с именем
        builder.add(InlineKeyboardButton(text=name, callback_data=f"st_name_{tg_id}"))
        # 2. Кнопка с балансом
        builder.add(InlineKeyboardButton(text=get_emoji_number(balance), callback_data=f"st_bal_{tg_id}"))
        # 3. Кнопка со статусом ДЗ
        builder.add(InlineKeyboardButton(text=hw_icon, callback_data=f"st_hw_{tg_id}"))

    # Группируем по 3 кнопки в ряд (получится ровная таблица)
    builder.adjust(3)

    await message.answer(
        "📋 **Ваши студенты:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


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


# Регистрация общих хендлеров для этого роутера
router.callback_query.register(
    show_day_actions,
    F.data.startswith("calendar_day_") | F.data.startswith("std_day_"),
    StateFilter(None)
)
router.callback_query.register(resched_start, F.data.startswith("resched_start_"))
router.callback_query.register(resched_date_chosen, RescheduleState.waiting_for_new_date, F.data.startswith("calendar_day_"))
router.callback_query.register(resched_final, RescheduleState.waiting_for_new_time, F.data.startswith("set_time_"))