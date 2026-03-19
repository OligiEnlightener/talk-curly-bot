from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID
from keyboards import get_admin_kb, get_student_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Пытаемся удалить сообщение /start от пользователя для чистоты чата
    try:
        await message.delete()
    except:
        pass

    if message.from_user.id == ADMIN_ID:
        # Меню для ВАС
        await message.answer(
            "⬥ **Панель управления Talk Curly** ⬥\n\n"
            "Шеф, все системы работают в штатном режиме.\n"
            "Выберите нужное действие в меню ниже:",
            reply_markup=get_admin_kb(), # Используем админскую клавиатуру
            parse_mode="Markdown"
        )
    else:
        # Меню для СТУДЕНТА
        await message.answer(
            "⬥ **Talk Curly Bot** ⬥\n\n"
            "Привет! Я твой личный помощник по занятиям.\n"
            "Здесь ты можешь проверить остаток уроков или сдать ДЗ.\n"
            "Меню всегда доступно в нижней части экрана. 👇",
            reply_markup=get_student_kb(), # Используем студенческую клавиатуру
            parse_mode="Markdown"
        )


@router.message(F.text == "📅 Расписание")
async def show_schedule_menu(message: types.Message):
    builder = InlineKeyboardBuilder()

    if message.from_user.id == ADMIN_ID:
        # Меню для преподавателя
        builder.button(text="Сегодня", callback_data="sched_day")
        builder.button(text="На неделю", callback_data="sched_week")
        builder.button(text="На месяц", callback_data="sched_month")
    else:
        # Меню для студента
        builder.button(text="Моя неделя", callback_data="sched_week")
        builder.button(text="Мой месяц", callback_data="sched_month")

    builder.adjust(1)
    await message.answer("Выберите период планирования:", reply_markup=builder.as_markup())