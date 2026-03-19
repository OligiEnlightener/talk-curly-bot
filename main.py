import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import API_TOKEN, ADMIN_ID

# Импортируем роутеры из ваших новых файлов
from handlers.admin import router as admin_router
from handlers.student import router as student_router

# Импортируем фоновую задачу и команду старта
from handlers.admin import check_lessons_loop
from handlers.common import router as common_router  # Если создали отдельный для /start


async def main():
    # Настройка логирования (поможет видеть ошибки в консоли)
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    # --- РЕГИСТРАЦИЯ РОУТЕРОВ ---
    # Важно: admin_router лучше ставить выше, если там есть строгие фильтры
    dp.include_router(admin_router)
    dp.include_router(common_router)  # Для команды /start
    dp.include_router(student_router)

    # --- ЗАПУСК ФОНОВЫХ ЗАДАЧ ---
    # Запускаем цикл проверки прошедших уроков в "фоне"
    asyncio.create_task(check_lessons_loop(bot))

    print("🚀 Бот Talk Curly запущен и готов к работе!")

    # Пропускаем накопившиеся сообщения и запускаем опрос
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")