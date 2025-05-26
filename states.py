from aiogram.dispatcher.filters.state import State, StatesGroup

class WbDetailsState(StatesGroup):
    download_wb_details = State()


class SelfPayments(StatesGroup):
    download_self_payments = State()


class CostPrices(StatesGroup):
    download_cost_price = State()


class Advertisement(StatesGroup):
    download_advertisement = State()


class GenerateFullUnitEconomy(StatesGroup):
    write_staff_data = State()


class GetOPI(StatesGroup):
    waiting_for_brand_name = State()
    waiting_for_start_date = State()
    waiting_for_finish_date = State()


class GetUnitEconomy(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_finish_date = State()


class OtherInformation(StatesGroup):
    download_other_information = State()


class DownloadСheque(StatesGroup):
    download_cheque = State()


class DownloadFirstTime(StatesGroup):
    download_seller_url = State()
    download_other_information = State()


class WritePromoCode(StatesGroup):
    send_promo_code = State()

class WriteTaxRate(StatesGroup):
    send_tax = State()


class Questions(StatesGroup):
    extra_report = State()
    costs = State()
    costs_change = State()
    advertisements = State()
    other_expenses = State()
    selfs = State()
    finish = State()
    items_without_costs = State()
