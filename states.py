from aiogram.fsm.state import StatesGroup, State


class AddToken(StatesGroup):
    wait = State()


class AddWarehouse(StatesGroup):
    name = State()
    coefficient = State()
    start_date = State()
    confirm = State()


class ChangeWarehouse(StatesGroup):
    coefficient = State()
    start_date = State()
    finish_date = State()
