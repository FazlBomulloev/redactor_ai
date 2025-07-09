from functools import wraps
from pyexpat.errors import messages
from statistics import median

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    Message,
    PhotoSize,
    Video,
    InputMedia,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.repositories import ThematicBlockRepository
from core.repositories.admin import AdminRepository
from core.repositories.publication import PublicationRepository
from core.repositories.publication_schedule import PublicationScheduleRepository
from routers.publication_schedule import AddTime
from utils.adm import check_permission
from utils.create_keyboard import create_kb

publication_router = Router()
repo = PublicationRepository()
repo_sh = PublicationScheduleRepository()


class CreatePublication(StatesGroup):
    name = State()
    text = State()
    media = State()
    cb_qr: CallbackQuery


class ChangeP(StatesGroup):
    model: list
    value = State()
    mess_id: int


class AddPub(StatesGroup):
    name: str
    time = State()


@publication_router.callback_query(F.data == "publications")
@check_permission("publication")
async def publication_menu(callback_query: CallbackQuery, state: FSMContext):
    try:
        publs = await repo.select_all()
        await state.clear()

        # Проверяем, есть ли текст в исходном сообщении
        if callback_query.message.text:
            await callback_query.message.edit_text(
                "Публикации", reply_markup=await create_kb.create_publication(publs)
            )
        else:
            # Если текста нет, отправляем новое сообщение
            await callback_query.message.answer(
                "Публикации", reply_markup=await create_kb.create_publication(publs)
            )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка1: {str(e)}")


@publication_router.callback_query(F.data.startswith("pub_"))
async def publication_menu(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        pb = await repo.select_name(data[1])
        kb = InlineKeyboardBuilder()
        btn_edit_text = InlineKeyboardButton(
            text="Заменить текст", callback_data=f"editpub_text_{pb.name}"
        )
        btn_edit_media = InlineKeyboardButton(
            text="Заменить медиа", callback_data=f"editpub_media_{pb.name}"
        )
        btn_edit_del = InlineKeyboardButton(
            text="Удалить публикацию", callback_data=f"editpub_del_{pb.name}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="publications")
        kb.row(btn_edit_text)
        kb.row(btn_edit_media)
        kb.row(btn_edit_del)
        kb.row(btn_back)

        # Проверка типа файла и отправка соответствующего медиа
        if pb.media.startswith(
            "AgAC"
        ):  # Предположим, что file_id фото начинается с "AgAC"
            await callback_query.message.answer_photo(
                pb.media, caption=pb.text, reply_markup=kb.as_markup()
            )
        elif pb.media.startswith(
            "BAAC"
        ):  # Предположим, что file_id видео начинается с "BAAC"
            await callback_query.message.answer_video(
                pb.media, caption=pb.text, reply_markup=kb.as_markup()
            )
        else:
            await callback_query.message.answer("Неподдерживаемый тип медиа.")
    except Exception as e:
        print(e)
        await callback_query.message.answer(f"Ошибка2: {str(e)}")


@publication_router.callback_query(F.data.startswith("editpub_"))
async def edit_pub(callback_query: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        data = callback_query.data.split("_")
        ChangeP.model = data
        print(ChangeP.model)
        if data[1] == "text":
            await callback_query.message.answer("Введите текст")
            await state.set_state(ChangeP.value)
        elif data[1] == "media":
            await callback_query.message.answer("Введите медиа")
            await state.set_state(ChangeP.value)
        elif data[1] == "del":
            pb = await repo.select_name(data[2])
            await repo.delete(pb.id)
            await repo_sh.delete_pb_id(pb.id)
            kb = InlineKeyboardBuilder()
            kb.add(InlineKeyboardButton(text="Назад", callback_data="publications"))
            await callback_query.message.answer("Удалено", reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка3: {str(e)}")


@publication_router.message(ChangeP.value)
async def description_block(message: Message, state: FSMContext):
    try:
        mess = message.text
        if ChangeP.model[1] == "media":
            if message.text == "0":
                mess = ""
            else:
                if message.photo and isinstance(message.photo[0], PhotoSize):
                    mess = message.photo[0].file_id
                elif message.video and isinstance(message.video, Video):
                    mess = message.video.file_id
                else:
                    return
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="publications"))
        await state.update_data(value=mess)
        data = await state.get_data()
        await repo.update(ChangeP.model[2], ChangeP.model[1], data.get("value"))

        await message.answer("Изменено", reply_markup=kb.as_markup())
        await state.clear()
    except Exception as e:
        print(ChangeP.model)
        await message.answer(f"Ошибка4: {e}")


@publication_router.callback_query(F.data == "create_publication")
async def create_publication(callback_query: CallbackQuery, state: FSMContext):
    try:
        CreatePublication.cb_qr = callback_query
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="publications")
        kb.row(btn_back)
        await callback_query.message.edit_text(
            "Введите название не больше 20 знаков", reply_markup=kb.as_markup()
        )

        await state.set_state(CreatePublication.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка5: {str(e)}")


@publication_router.message(CreatePublication.name)
async def create_name(message: Message, state: FSMContext):
    try:
        if len(message.text) > 20:
            await message.answer("название больше 20 знаков")
            await create_publication(CreatePublication.cb_qr, state)
            return
        if message.text != "":
            await state.update_data(name=message.text)
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="create_publication"
        )
        kb.row(btn_back)
        await message.answer("Введите текст", reply_markup=kb.as_markup())

        await state.set_state(CreatePublication.text)
    except Exception as e:
        await message.answer(f"Ошибка6: {str(e)}")


@publication_router.callback_query(F.data.startswith("backpub_"))
async def create_publication(callback_query: CallbackQuery, state: FSMContext):
    try:
        print(0)
        data = callback_query.data.split("_")[1]
        if data == "text":
            print(1)
            await state.set_state(CreatePublication.name)
            await create_name(callback_query.message, state)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка7: {str(e)}")


@publication_router.message(CreatePublication.text)
async def create_media(message: Message, state: FSMContext):
    try:
        await state.update_data(text=message.text)
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="backpub_text")
        kb.row(btn_back)
        await message.answer(
            "Введите медиа\nЕсли медиа нет отправь 0", reply_markup=kb.as_markup()
        )

        await state.set_state(CreatePublication.media)
    except Exception as e:
        await message.answer(f"Ошибка8: {str(e)}")


@publication_router.message(CreatePublication.media)
async def create_publication(message: Message, state: FSMContext):
    try:
        if message.text == "0":
            media = ""
        else:
            if message.photo and isinstance(message.photo[0], PhotoSize):
                media = message.photo[0].file_id
                print(media)
            elif message.video and isinstance(message.video, Video):
                media = message.video.file_id
                print(media)
            else:
                await message.answer("Пожалуйста, отправьте фото или видео.")
                return

        await state.update_data(media=media)

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="publications")
        kb.row(btn_back)

        data = await state.get_data()
        await repo.add(data.get("name"), data.get("text"), data.get("media"))
        await message.answer("OK", reply_markup=kb.as_markup())
        await state.clear()
    except Exception as e:
        print(e)
        print(message)
        await message.answer(f"Ошибка9: {str(e)}")


@publication_router.callback_query(F.data == "select_publications_fl")
async def schedule_pubs(callback_query: CallbackQuery):
    try:
        publs = await repo.select_all()

        # Проверяем, есть ли текст в исходном сообщении
        if callback_query.message.text:
            await callback_query.message.edit_text(
                "Публикации", reply_markup=await create_kb.add_publication(publs)
            )
        else:
            # Если текста нет, отправляем новое сообщение
            await callback_query.message.answer(
                "Публикации", reply_markup=await create_kb.add_publication(publs)
            )
    except Exception as e:
        print(e)
        await callback_query.message.answer(f"Ошибка10: {str(e)}")


@publication_router.callback_query(F.data.startswith("addpub_"))
async def schedule_pubs(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_back)
        AddPub.name = callback_query.data.split("_")[1]
        pb = await repo.select_name(AddPub.name)
        await repo_sh.add(AddTime.time_in_pb, "0", AddTime.today, pb.id)
        await callback_query.message.answer("Успешно", reply_markup=kb.as_markup())
    except Exception as e:
        print(e)
        await callback_query.message.answer(f"Ошибка11: {str(e)}")
