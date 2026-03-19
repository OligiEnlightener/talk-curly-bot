from aiogram import F, types, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import ADMIN_ID
from database import get_lessons_by_date, reschedule_lesson, update_obsidian_json
from states import RescheduleState
from utils.calendar_grid import generate_calendar, generate_time_grid

router = Router()


@router.callback_query(
    StateFilter(None),
    F.data.startswith("calendar_day_") | F.data.startswith("std_day_")
)
async def show_day_actions(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")

    # Логика разбора даты в зависимости от того, кто нажал
    if callback.data.startswith("std_day_"):
        # Студент: std_day_2026-03-19
        date_str = data_parts[2]
        day_display = ".".join(date_str.split("-")[1:][::-1])
    else:
        # Админ: calendar_day_2026_03_19
        year, month, day = data_parts[2], data_parts[3], data_parts[4]
        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
        day_display = f"{day}.{month}"

    user_id = callback.from_user.id
    # Админ видит всех, студент только себя
    student_id = None if user_id == ADMIN_ID else user_id

    lessons = get_lessons_by_date(date_str, student_id=student_id)

    if not lessons:
        await callback.answer(f"На {day_display} уроков нет", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for name, full_time, hw, lesson_id in lessons:
        time_only = full_time.split(' ')[1]
        # Для админа пишем имя ученика, для ученика — просто время
        label = f"⏰ {time_only} - {name}" if user_id == ADMIN_ID else f"⏰ {time_only}"

        builder.add(InlineKeyboardButton(text=label, callback_data="ignore"))
        builder.add(InlineKeyboardButton(text="🔄 Перенести", callback_data=f"resched_start_{lesson_id}"))

    builder.adjust(2)

    # Кнопка возврата: админа в календарь, студента в неделю
    back_cmd = "back_to_cal" if user_id == ADMIN_ID else "sched_week"
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cmd))

    await callback.message.edit_text(
        f"📅 Уроки на {day_display}:",
        reply_markup=builder.as_markup()
    )
    # КРИТИЧНО: этот ответ убирает "загрузку"
    await callback.answer()


# --- ЛОГИКА ПЕРЕНОСА (остается почти без изменений, но добавим answer) ---

@router.callback_query(RescheduleState.waiting_for_new_date, F.data.startswith("calendar_day_"))
async def resched_date_chosen(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split("_")
    year, month, day = data_parts[2], data_parts[3], data_parts[4]
    new_date = f"{year}-{int(month):02d}-{int(day):02d}"

    await state.update_data(new_date=new_date)

    await callback.message.edit_text(
        f"Выбрана дата {day}.{month}. Теперь выберите время:",
        reply_markup=generate_time_grid(None, new_date)
    )
    await state.set_state(RescheduleState.waiting_for_new_time)
    await callback.answer()

@router.callback_query(F.data.startswith("resched_start_"))
async def resched_start(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = callback.data.split("_")[2]
    await state.update_data(resched_lesson_id=lesson_id)

    await callback.message.edit_text(
        "Выберите НОВУЮ дату для переноса уроков:",
        reply_markup=generate_calendar()
    )
    await state.set_state(RescheduleState.waiting_for_new_date)
    await callback.answer()



@router.callback_query(RescheduleState.waiting_for_new_time, F.data.startswith("set_time_"))
async def resched_final(callback: types.CallbackQuery, state: FSMContext):
    time_val = callback.data.split("_")[4]
    user_data = await state.get_data()

    new_datetime = f"{user_data['new_date']} {time_val}"
    reschedule_lesson(user_data['resched_lesson_id'], new_datetime)
    update_obsidian_json()

    await callback.message.edit_text(f"✅ Урок успешно перенесен на {new_datetime}")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "back_to_cal")
async def back_to_calendar(callback: types.CallbackQuery):
    await callback.message.edit_text("Ваш календарь занятий:", reply_markup=generate_calendar())
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: types.CallbackQuery):
    await callback.answer()