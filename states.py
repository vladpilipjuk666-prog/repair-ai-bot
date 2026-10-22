"""FSM-состояния."""

from aiogram.fsm.state import State, StatesGroup


class RequestForm(StatesGroup):
    device_type = State()
    device_model = State()
    problem = State()
    photos = State()
    processing = State()
    service_method = State()
    address = State()
    name = State()
    phone = State()
    confirm = State()


class AdminFlow(StatesGroup):
    price = State()
    price_comment = State()
    message = State()


class ReviewFlow(StatesGroup):
    text = State()
