from aiogram.fsm.state import StatesGroup, State


class RegisterStudent(StatesGroup):
    waiting_for_contact = State()
    waiting_for_balance = State()

class ScheduleLesson(StatesGroup):
    waiting_for_name = State()
    waiting_for_datetime = State()

class ScheduleLesson(StatesGroup):
    waiting_for_student = State()
    waiting_for_date = State()
    waiting_for_time = State()

class RescheduleState(StatesGroup):
    waiting_for_new_date = State()
    waiting_for_new_time = State()