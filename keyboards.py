from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def get_main_kb():
    """Создает постоянные кнопки внизу экрана"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📊 Мой баланс")
    kb.button(text="✅ ДЗ сделано")
    kb.button(text="📚 Hausaufgaben")
    kb.button(text="📚 Расписание")
    kb.adjust(2)  # Две кнопки в ряд
    return kb.as_markup(resize_keyboard=True)

def get_admin_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="👥 Список студентов")
    kb.button(text="➕ Добавить студента")
    kb.button(text="📅 Запланировать") # Новая кнопка
    kb.button(text="📚 Расписание")
    kb.adjust(3)
    return kb.as_markup(resize_keyboard=True)

def get_student_kb():
    """Кнопки для ученика"""
    kb = ReplyKeyboardBuilder()
    kb.button(text="📊 Мой баланс")
    kb.button(text="✅ ДЗ сделано")
    kb.button(text="📅 Мои уроки")
    kb.adjust(3) # Две кнопки в один ряд
    return kb.as_markup(resize_keyboard=True)

