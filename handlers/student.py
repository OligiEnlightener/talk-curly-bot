from datetime import datetime
import sqlite3
from aiogram import F, types, Router
from config import ADMIN_ID, DB_PATH
from database import get_emoji_number, update_obsidian_json
from utils.calendar_grid import get_student_week_grid

router = Router()

@router.message(F.text == "📊 Мой баланс")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance FROM students WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()

    if result:
        name, balance = result
        await message.answer(f"Твой баланс: {get_emoji_number(balance)}")
    else:
        await message.answer("Вас пока нет в системе.")

@router.message(F.text == "✅ ДЗ сделано")
async def hw_done_button(message: types.Message):
    user_id = message.from_user.id
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM students WHERE telegram_id = ?", (user_id,))
        res = cursor.fetchone()

        if res:
            name = res[0]
            cursor.execute("UPDATE students SET hw_status = '✅ Готово' WHERE telegram_id = ?", (user_id,))
            conn.commit()
            update_obsidian_json()
            await message.bot.send_message(ADMIN_ID, f"🔔 **{name}** сдал домашку!")
            await message.answer("Супер! Передал информацию преподавателю.")
        else:
            await message.answer("Сначала нужно зарегистрироваться.")

@router.message(F.text == "📅 Мои уроки")
async def show_student_lessons_cmd(message: types.Message):
    await message.answer(
        "Твое расписание на текущую неделю:\n(Дни с занятиями помечены 🔴)",
        reply_markup=get_student_week_grid(message.from_user.id)
    )

@router.callback_query(F.data == "sched_week")
async def show_student_week_callback(callback: types.CallbackQuery):
    markup = get_student_week_grid(callback.from_user.id)
    await callback.message.edit_text("Ваша неделя занятий (🔴 — есть урок):", reply_markup=markup)

@router.callback_query(F.data.startswith("std_day_"))
async def student_day_info(callback: types.CallbackQuery):
    # Разбираем std_day_2026-03-19
    date_str = callback.data.split("_")[2]
    student_id = callback.from_user.id

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT lesson_time FROM lessons 
            WHERE student_id = ? AND lesson_time LIKE ? AND status != 'cancelled'
        ''', (student_id, f"{date_str}%"))
        lesson = cursor.fetchone()

    if lesson:
        time_only = lesson[0].split(" ")[1]
        await callback.answer(f"У вас урок в {time_only}", show_alert=True)
    else:
        await callback.answer("В этот день занятий нет ☕️", show_alert=True)