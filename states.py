from aiogram.fsm.state import StatesGroup, State


class AddToken(StatesGroup):
    wait = State()


class AddWarehouse(StatesGroup):
    name = State()
    coefficient = State()
    interval = State()
    confirm = State()


class ChangeWarehouse(StatesGroup):
    coefficient = State()
    interval = State()
