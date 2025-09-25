from aiogram.fsm.state import State, StatesGroup


class CarState(StatesGroup):
    number = State()
    upload_date = State()
    current_date = State()
    cities = State()
    type_car = State()
    manager_number = State()
    manager_name = State()
    manager_email = State()

class CargoState(StatesGroup):
    number = State()
    upload_date = State()
    current_date = State()
    cities = State()
    type_car = State()
    manager_number = State()
    manager_name = State()
    manager_email = State()

class SearchState(StatesGroup):
    search_date = State()
    search_city = State()
    search_type = State()