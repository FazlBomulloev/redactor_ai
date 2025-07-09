from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.repositories import ThematicBlockRepository
from core.repositories.event import EventRepository
from utils.adm import check_permission
from utils.create_keyboard import create_kb

event_router = Router()
repo = EventRepository()


class Event(StatesGroup):
    event = State()
    edit_name = State()


class Change_ev(StatesGroup):
    model: str
    value = State()
    mess_id: int


class CreateEvent(StatesGroup):
    name = State()
    source = State()
    description = State()
    stop_description = State()
    interval = State()
    time_in = State()
    time_out = State()
    cb_qr: CallbackQuery


@event_router.callback_query(F.data == "event")
@check_permission("event")
async def event_menu(callback_query: CallbackQuery):
    try:
        await callback_query.message.edit_text(
            "События:", reply_markup=await create_kb.create_ps_event()
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data == "list_events")
async def event_list(callback_query: CallbackQuery, state: FSMContext):
    try:
        event_list = await repo.select_all()
        page = 0  # Начальная страница
        page_size = 20

        total_pages = (len(event_list) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_events = event_list[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for event in current_page_events:
            btn = InlineKeyboardButton(
                text=f"{event.name}", callback_data=f"select_event_{event.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"events_{page-1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"events_{page+1}"
                )
                kb.row(btn_next)

        btn_back = InlineKeyboardButton(text="Назад", callback_data="event")
        kb.row(btn_back)

        await callback_query.message.edit_text(
            "Выберите событие:", reply_markup=kb.as_markup()
        )
        await state.set_state(Event.event)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("events_"))
async def event_list_pagination(callback_query: CallbackQuery, state: FSMContext):
    try:
        page = int(callback_query.data.split("_")[1])
        event_list = await repo.select_all()
        page_size = 20

        total_pages = (len(event_list) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_events = event_list[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for event in current_page_events:
            btn = InlineKeyboardButton(
                text=f"{event.name}", callback_data=f"select_event_{event.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"events_{page-1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"events_{page+1}"
                )
                kb.row(btn_next)

        btn_back = InlineKeyboardButton(text="Назад", callback_data="event")
        kb.row(btn_back)

        await callback_query.message.edit_text(
            "Выберите событие:", reply_markup=kb.as_markup()
        )
        await state.set_state(Event.event)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("select_event_"))
async def event_detail(callback_query: CallbackQuery, state: FSMContext):
    try:
        event_id = callback_query.data.split("_")[2]
        event = await repo.select_id(event_id)
        kb = InlineKeyboardBuilder()
        btn_edit_name = InlineKeyboardButton(
            text="Изменить название", callback_data=f"edit_event_name_{event_id}"
        )
        btn_edit_source = InlineKeyboardButton(
            text="Изменить источник", callback_data=f"edit_event_source_{event_id}"
        )
        btn_edit_description = InlineKeyboardButton(
            text="Изменить описание", callback_data=f"edit_event_description_{event_id}"
        )
        btn_edit_stop_description = InlineKeyboardButton(
            text="Изменить стоп-темы",
            callback_data=f"edit_event_stop_description_{event_id}",
        )
        btn_edit_interval = InlineKeyboardButton(
            text="Изменить промежуток времени",
            callback_data=f"edit_event_interval_{event_id}",
        )
        btn_edit_time_in = InlineKeyboardButton(
            text="Изменить первую точку времени",
            callback_data=f"edit_event_time_in_{event_id}",
        )
        btn_edit_time_out = InlineKeyboardButton(
            text="Изменить вторую точку времени",
            callback_data=f"edit_event_time_out_{event_id}",
        )
        btn_delete = InlineKeyboardButton(
            text="Удалить", callback_data=f"delete_event_{event_id}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="list_events")
        kb.row(btn_edit_name)
        kb.row(btn_edit_source)
        kb.row(btn_edit_description)
        kb.row(btn_edit_stop_description)
        kb.row(btn_edit_interval)
        kb.row(btn_edit_time_in)
        kb.row(btn_edit_time_out)
        kb.row(btn_delete)
        kb.row(btn_back)

        text = (
            f"Описание: {event.description}\n"
            f"Источники: {event.source}\n"
            f"Промежуток времени: {event.interval} минут\n"
            f"Время работы: с {event.time_in} до {event.time_out}\n"
            f"Стоп-темы: {event.stop_description}"
        )

        await callback_query.message.edit_text(
            text,
            reply_markup=kb.as_markup(),
        )
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("delete_event_"))
async def delete_event(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        event_id = callback_query.data.split("_")[2]
        await repo.delete(int(event_id))
        btn_back = InlineKeyboardButton(text="Назад", callback_data="list_events")
        kb.row(btn_back)
        await callback_query.message.edit_text(
            "Событие удалено.", reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("edit_event_"))
async def edit_event(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split("_")
        if "time" or "stop" in data:
            Change_ev.model = data[2] + "_" + data[3]
            await state.update_data(event_id=data[4])

        else:
            Change_ev.model = data[2]
            await state.update_data(event_id=data[3])
        Change_ev.mess_id = callback_query.message.message_id
        await callback_query.message.answer("Введите новое значение")
        await state.set_state(Change_ev.value)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(Change_ev.value)
async def update_event(message: Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    try:
        await state.update_data(value=message.text)
        data = await state.get_data()
        model = Change_ev.model
        event_id = data.get("event_id")
        await repo.update(int(event_id), model, data.get("value"))
        btn_back = InlineKeyboardButton(text="Назад", callback_data=f"list_events")
        kb.row(btn_back)
        await message.answer("Событие обновлено", reply_markup=kb.as_markup())
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data == "add_event")
async def create_event(callback_query: CallbackQuery, state: FSMContext):
    try:
        CreateEvent.cb_qr = callback_query
        await callback_query.message.answer("Введите название не больше 20 знаков")
        await state.set_state(CreateEvent.name)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.name)
async def source_block(message: Message, state: FSMContext):
    try:
        if len(message.text) > 20:
            await message.answer("название больше 20 знаков")
            await create_event(CreateEvent.cb_qr, state)
            return
        await message.answer("Введите источник")
        await state.update_data(name=message.text)
        await state.set_state(CreateEvent.source)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.source)
async def description_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите описание")
        await state.update_data(source=message.text)
        await state.set_state(CreateEvent.description)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.description)
async def stop_description_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите стоп-темы")
        await state.update_data(description=message.text)
        await state.set_state(CreateEvent.stop_description)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.stop_description)
async def interval_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите промежуток времени (в минутах)")
        await state.update_data(stop_description=message.text)
        await state.set_state(CreateEvent.interval)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.interval)
async def time_in_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите первую точку времени (в формате HH:MM)")
        await state.update_data(interval=message.text)
        await state.set_state(CreateEvent.time_in)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.time_in)
async def time_out_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите вторую точку времени (в формате HH:MM)")
        await state.update_data(time_in=message.text)
        await state.set_state(CreateEvent.time_out)
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(CreateEvent.time_out)
async def finalize_event(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="list_events"))
        await state.update_data(time_out=message.text)
        data = await state.get_data()
        await repo.add(
            data.get("name"),
            data.get("source"),
            data.get("description"),
            data.get("stop_description"),
            data.get("interval"),
            data.get("time_in"),
            data.get("time_out"),
        )
        await message.answer(
            f"Событие: {data.get('name')}\nУспешно создано", reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("edit_event"))
async def change_mess(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        print(data)
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_kb.create_ev_individual(data[2])
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.callback_query(F.data.startswith("evchange_"))
async def create_change_mess_ev(callback_query: CallbackQuery, state: FSMContext):
    try:
        change = callback_query.data.split("_")
        Change_ev.model = change
        Change_ev.mess_id = callback_query.message.business_connection_id
        await callback_query.message.answer("Введите новое значение")
        await state.set_state(Change_ev.value)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@event_router.message(Change_ev.value)
async def description_block(message: Message, state: FSMContext):
    try:
        await state.update_data(value=message.text)
        data = await state.get_data()
        model = Change_ev.model
        print(model)
        q = await repo.update(
            model[2] if len(model) < 4 else model[3],
            model[1] + ("_" + model[2] if len(model) == 4 else ""),
            data.get("value"),
        )
        await message.answer("OK")
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")
