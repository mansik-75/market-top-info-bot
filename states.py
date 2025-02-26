
from aiogram.fsm.state import State, StatesGroup


class DownloadAPIKey(StatesGroup):
    key = State()
    key_type = State()
    key_type_save = State()
    email = State()
