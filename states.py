from aiogram.fsm.state import StatesGroup, State


class RegisterStudent(StatesGroup):
    waiting_for_contact = State()
    waiting_for_balance = State()

class ScheduleLesson(StatesGroup):
    waiting_for_name = State()
    waiting_for_datetime = State()