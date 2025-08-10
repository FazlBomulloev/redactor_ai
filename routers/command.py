from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from utils.adm import super_adm

from utils.create_keyboard import create_kb

from core.repositories.admin import AdminRepository

repo_admin = AdminRepository()
command_router = Router()


@command_router.message(Command("start"))
async def process_start_command(message: types.Message):
    adms = await repo_admin.select_all()
    adms_lis = []
    for adm in adms:
        adms_lis.append(int(adm.admin_id))
    if (
        int(message.from_user.id) not in adms_lis
        and int(message.from_user.id) not in super_adm
    ):
        return
    buttons = ["Меню"]
    start_txt = "Привет"
    await message.answer(
        start_txt, reply_markup=await create_kb.create_keyboard(buttons)
    )


@command_router.message(F.text == "Меню")
async def inline_menu(message: types.Message):
    adms = await repo_admin.select_all()
    adms_lis = []
    for adm in adms:
        adms_lis.append(int(adm.admin_id))
    if (
        int(message.from_user.id) not in adms_lis
        and int(message.from_user.id) not in super_adm
    ):
        return
    await message.answer(
        "Меню:",
        reply_markup=await create_kb.create_kb_menu(super_adm, message.from_user.id),
    )


@command_router.callback_query(F.data == "back_to_main")
async def back_menu(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "Menu",
        reply_markup=await create_kb.create_kb_menu(
            super_adm, callback_query.from_user.id
        ),
    )
