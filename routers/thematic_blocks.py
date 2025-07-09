from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.repositories.publication_schedule import PublicationScheduleRepository
from utils.adm import check_permission
from utils.create_keyboard import create_kb
from core.repositories.thematic_block import ThematicBlockRepository
from core.repositories.folder import FolderRepository

thematic_blocks_router = Router()
repo = ThematicBlockRepository()
repo_fl = FolderRepository()
repo_pb = PublicationScheduleRepository()


class CreateBlock(StatesGroup):
    name = State()
    source = State()
    description = State()
    time_back = State()
    stop_words = State()
    folder: str
    cb_qr: CallbackQuery


class CreateFolder(StatesGroup):
    name = State()
    cb_qr: CallbackQuery


class ChangeFolder(StatesGroup):
    name = State()
    model: str


class Change(StatesGroup):
    model: str
    value = State()
    mess_id: int


@thematic_blocks_router.callback_query(F.data == "thematic_blocks")
@check_permission("thematickblock")
async def thematic_blocks_folder_menu(callback_query: CallbackQuery):
    try:
        list_fl = await repo_fl.select_all()
        await callback_query.message.edit_text(
            "Папки:", reply_markup=await create_kb.create_folder(list_fl)
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("fl_"))
async def thematic_blocks_menu(callback_query: CallbackQuery):
    try:
        fl_name = callback_query.data.split("_")[1]
        fl = await repo_fl.select_name(fl_name)
        CreateBlock.folder = fl
        list_fl = await repo.select_id_folder(fl.id)
        await callback_query.message.edit_text(
            "TB:", reply_markup=await create_kb.create_tb(list_fl, fl_name)
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("changefl_"))
async def thematic_blocks_menu(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split("_")
        if data[1] == "del":
            fl = await repo_fl.select_name(data[2])
            await repo.delete_fl_id(fl.id)
            await repo_fl.delete(data[2])
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
            await callback_query.message.answer(
                f"Папка: {data[2]}\n Успешно удалена", reply_markup=kb.as_markup()
            )
        elif data[1] == "name":
            ChangeFolder.model = data[2]
            await callback_query.message.answer("Введите название")
            await state.set_state(ChangeFolder.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(ChangeFolder.name)
async def description_block(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        await state.update_data(name=message.text)
        data = await state.get_data()
        await repo_fl.update(ChangeFolder.model, "name", data.get("name"))
        await message.answer(
            f"Папка: {data.get('name')}\nУспешно изменена", reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data == "create_folder")
async def create_fold(callback_query: CallbackQuery, state: FSMContext):
    try:
        CreateFolder.cb_qr = callback_query
        await callback_query.message.answer("Введите название не больше 20 знаков")
        await state.set_state(CreateFolder.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateFolder.name)
async def description_block(message: Message, state: FSMContext):
    try:
        if len(message.text) > 20:
            await message.answer("название больше 20 знаков")
            await create_fold(CreateFolder.cb_qr, state)
            return
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        await state.update_data(name=message.text)
        data = await state.get_data()
        await repo_fl.add(
            data.get("name"),
        )
        await message.answer(
            f"Папка: {data.get('name')}\nУспешно создан", reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("tb_"))
async def thematic_block(callback_query: CallbackQuery):
    try:
        form_text = ""
        name_tb = callback_query.data.split("_")
        name_tb = name_tb[1]
        name_tb = await repo.select_name(name_tb)
        form_text += name_tb.name + "\n"
        form_text += f"Источники: {name_tb.source}\n"
        form_text += f"Время: {name_tb.time_back}\n"
        form_text += f"Стоп-слова: {name_tb.stop_words}\n"
        form_text += f"Описание: {name_tb.description}"

        await callback_query.message.edit_text(
            form_text, reply_markup=await create_kb.create_tb_individual(name_tb.name)
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("create_block"))
async def create_block(callback_query: CallbackQuery, state: FSMContext):
    try:
        CreateBlock.cb_qr = callback_query
        await callback_query.message.answer("Введите название не больше 20 знаков")
        await state.set_state(CreateBlock.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.name)
async def source_block(message: Message, state: FSMContext):
    try:
        if len(message.text) > 20:
            await message.answer("название больше 20 знаков")
            await create_block(CreateBlock.cb_qr, state)
            return
        await message.answer("Введите источник")
        await state.update_data(name=message.text)
        await state.set_state(CreateBlock.source)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.source)
async def description_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите стоп-слова")
        await state.update_data(source=message.text)
        await state.set_state(CreateBlock.stop_words)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.stop_words)
async def description_block(message: Message, state: FSMContext):
    try:
        await message.answer(
            "Введите время за которое нужно просмотреть посты в минутах"
        )
        await state.update_data(stop_words=message.text)
        await state.set_state(CreateBlock.time_back)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.time_back)
async def description_block(message: Message, state: FSMContext):
    try:
        await message.answer("Введите описание")
        await state.update_data(time_back=message.text)
        await state.set_state(CreateBlock.description)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.description)
async def description_block(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        await state.update_data(description=message.text)
        data = await state.get_data()
        await repo.add(
            data.get("name"),
            data.get("source"),
            data.get("description"),
            data.get("time_back"),
            data.get("stop_words"),
            CreateBlock.folder,
        )
        await message.answer(
            f"ТБ: {data.get('name')}\nУспешно создан", reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("changetb"))
async def create_change_mess(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        change = callback_query.data.split("_")
        Change.model = change
        if change[1] == "delete":
            tb = await repo.select_name(change[2])
            await repo.delete(tb.id)
            await repo_pb.delete_tb_id(tb.id)
            await callback_query.message.edit_text(
                "Удалено", reply_markup=kb.as_markup()
            )
        Change.mess_id = callback_query.message.business_connection_id
        await callback_query.message.answer("Введите новое значение")
        await state.set_state(Change.value)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(Change.value)
async def description_block(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        await state.update_data(value=message.text)
        data = await state.get_data()
        model = Change.model
        if model[1] == "timeback":
            model[1] = "time_back"
        elif model[1] == "sw":
            model[1] = "stop_words"
        print(model)
        q = await repo.update(model[2], model[1], data.get("value"))

        await message.answer("Изменено", reply_markup=kb.as_markup())
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
