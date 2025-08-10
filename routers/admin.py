import os
from dotenv import set_key, load_dotenv
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.config import reload_settings
from utils.adm import check_permission, super_adm
from utils.create_keyboard import create_kb
from core.repositories.admin import AdminRepository
from utils.telethon import telegram_client_wrapper
from utils.account_manager import account_manager

ACCOUNTS_DIR = os.path.join(os.getcwd(), "accounts")

repo = AdminRepository()
admin_router = Router()


class Admin(StatesGroup):
    id_adm = State()
    update_channel_link = State()
    add_account = State()


class AccountDelete(StatesGroup):
    confirm_delete = State()


@check_permission("some_permission_field")
async def update_channel_link(message: Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        if user_id not in super_adm:
            await message.answer("У вас нет прав для выполнения этого действия.")
            return

        new_link = message.text.strip()
        if not new_link:
            await message.answer("Ссылка не может быть пустой.")
            return

        # Загружаем переменные окружения из файла .env
        load_dotenv()

        # Обновляем значение переменной в файле .env
        set_key(".env", "CHANNEL__LINK", str(new_link))

        # Обновляем значение переменной в текущем окружении
        os.environ["CHANNEL__LINK"] = str(new_link)

        await message.answer(f"Ссылка на канал успешно обновлена: {new_link}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data == "administration")
async def admin_menu(callback_query: CallbackQuery):
    try:
        kb = InlineKeyboardBuilder()
        btn_list = InlineKeyboardButton(
            text="Список админов", callback_data="admin_list"
        )
        btn_add_admin = InlineKeyboardButton(
            text="Добавить админа", callback_data="admin_add"
        )
        btn_add_account = InlineKeyboardButton(
            text="Добавить аккаунт", callback_data="admin_add_account"
        )
        btn_accounts_stats = InlineKeyboardButton(
            text="Статистика аккаунтов", callback_data="accounts_stats"
        )
        btn_delete_accounts = InlineKeyboardButton(
            text="Удалить аккаунты", callback_data="delete_accounts_list"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="back_to_main")
        
        kb.row(btn_list)
        kb.row(btn_add_admin)
        kb.row(btn_add_account, btn_delete_accounts)
        kb.row(btn_accounts_stats)

        user_id = callback_query.from_user.id
        if user_id in super_adm:
            btn_update_channel = InlineKeyboardButton(
                text="Изменить ссылку на канал", callback_data="update_channel_link"
            )
            
            btn_ai_management = InlineKeyboardButton(
                text="Управление ИИ", callback_data="ai_management"
            )
            kb.row(btn_update_channel)
            kb.row(btn_ai_management)

        kb.row(btn_back)
        await callback_query.message.edit_text("ADMINS", reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data == "accounts_stats")
async def accounts_stats(callback_query: CallbackQuery):
    """Показать статистику аккаунтов"""
    try:
        stats = await account_manager.get_account_stats()
        active_accounts = telegram_client_wrapper.get_account_count()
        current_account = telegram_client_wrapper.current_client_key or "Нет активного"
        
        text = f"📊 Статистика аккаунтов:\n\n"
        text += f"📁 Файлов сессий: {stats['total_accounts']}\n"
        text += f"🟢 Активных подключений: {active_accounts}\n"
        text += f"⚡ Текущий аккаунт: {current_account}\n\n"
        
        if stats['account_list']:
            text += "📋 Список файлов:\n"
            for i, account in enumerate(stats['account_list'][:10], 1):  # Показываем первые 10
                status = "🟢" if account in telegram_client_wrapper.get_account_list() else "⚪"
                text += f"{i}. {account} {status}\n"
                
            if len(stats['account_list']) > 10:
                text += f"... и еще {len(stats['account_list']) - 10} аккаунтов\n"
        else:
            text += "❌ Нет аккаунтов"

        kb = InlineKeyboardBuilder()
        btn_refresh = InlineKeyboardButton(text="🔄 Обновить", callback_data="accounts_stats")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="administration")
        kb.row(btn_refresh)
        kb.row(btn_back)

        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@admin_router.callback_query(F.data == "delete_accounts_list")
async def delete_accounts_list(callback_query: CallbackQuery):
    """Показать список аккаунтов для удаления"""
    try:
        accounts = telegram_client_wrapper.get_account_list()
        
        if not accounts:
            kb = InlineKeyboardBuilder()
            btn_back = InlineKeyboardButton(text="Назад", callback_data="administration")
            kb.row(btn_back)
            await callback_query.message.edit_text(
                "❌ Нет активных аккаунтов для удаления", 
                reply_markup=kb.as_markup()
            )
            return

        kb = InlineKeyboardBuilder()
        for account in accounts:
            btn = InlineKeyboardButton(
                text=f"🗑️ {account}", 
                callback_data=f"delete_account_confirm_{account}"
            )
            kb.row(btn)

        btn_back = InlineKeyboardButton(text="Назад", callback_data="administration")
        kb.row(btn_back)

        text = f"🗑️ Удаление аккаунтов\n\n"
        text += f"Активных аккаунтов: {len(accounts)}\n"
        text += "Выберите аккаунт для удаления:"

        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("delete_account_confirm_"))
async def delete_account_confirm(callback_query: CallbackQuery):
    """Подтверждение удаления аккаунта - первое предупреждение"""
    try:
        account_name = callback_query.data.replace("delete_account_confirm_", "")
        
        kb = InlineKeyboardBuilder()
        btn_confirm = InlineKeyboardButton(
            text="⚠️ Да, удалить", 
            callback_data=f"delete_account_final_{account_name}"
        )
        btn_cancel = InlineKeyboardButton(
            text="❌ Отмена", 
            callback_data="delete_accounts_list"
        )
        kb.row(btn_confirm)
        kb.row(btn_cancel)

        text = f"⚠️ ВНИМАНИЕ!\n\n"
        text += f"Вы действительно хотите удалить аккаунт:\n"
        text += f"📱 {account_name}\n\n"
        text += f"❗ Это действие нельзя отменить!\n"
        text += f"🗑️ Файл сессии будет удален навсегда"

        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("delete_account_final_"))
async def delete_account_final(callback_query: CallbackQuery):
    """Окончательное удаление аккаунта - второе подтверждение"""
    try:
        account_name = callback_query.data.replace("delete_account_final_", "")
        
        # Удаляем аккаунт
        success = await telegram_client_wrapper.remove_account_by_name(account_name)
        
        if success:
            remaining_accounts = telegram_client_wrapper.get_account_count()
            
            # Логируем удаление
            await account_manager.log_to_chat(
                f"🗑️ Account manually deleted: {account_name} | Remaining: {remaining_accounts}",
                "WARNING"
            )
            
            kb = InlineKeyboardBuilder()
            btn_back_list = InlineKeyboardButton(text="К списку", callback_data="delete_accounts_list")
            btn_back_admin = InlineKeyboardButton(text="В админку", callback_data="administration")
            kb.row(btn_back_list)
            kb.row(btn_back_admin)

            text = f"✅ Аккаунт удален!\n\n"
            text += f"🗑️ Удален: {account_name}\n"
            text += f"📊 Осталось аккаунтов: {remaining_accounts}"

            await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
        else:
            await callback_query.message.answer("❌ Ошибка при удалении аккаунта")
            
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@admin_router.callback_query(F.data == "admin_list")
async def admin_list(callback_query: CallbackQuery):
    try:
        adm_list = await repo.select_all()
        await callback_query.message.edit_text(
            "Выберите админа:", reply_markup=await create_kb.create_adm_list(adm_list)
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data == "admin_add")
async def admin_add_id(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Введите id:")
        await state.set_state(Admin.id_adm)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.message(Admin.id_adm)
async def admin_add_status(message: Message, state: FSMContext):
    try:
        await state.update_data(id_adm=message.text)
        data = await state.get_data()
        await repo.add(int(data.get("id_adm")))
        adm = await repo.select_adm_id(int(data.get("id_adm")))
        await message.answer(
            f"Админ с id {data.get('id_adm')} успешно создан\nНастройте права:",
            reply_markup=await create_kb.create_rights(adm),
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("ad_"))
async def admin(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        kb = InlineKeyboardBuilder()
        kb.row(
            InlineKeyboardButton(
                text="Показать права", callback_data=f"show_rights_{data[1]}"
            )
        )
        kb.row(
            InlineKeyboardButton(
                text="Удалить", callback_data=f"delete_admin_check_{data[1]}"
            )
        )
        kb.row(InlineKeyboardButton(text="Назад", callback_data="admin_list"))

        await callback_query.message.edit_text(
            f"id {data[1]}", reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("show_rights_"))
async def rights(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        adm = await repo.select_adm_id(int(data[2]))
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_kb.create_rights(adm)
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("show_redact_"))
async def rights(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        if data[2].lower() == "true":
            original_value = True
        elif data[2].lower() == "false":
            original_value = False
        await repo.update(
            adm_id=int(data[3]),
            column=data[4] + ("_" + data[5] if len(data) == 6 else ""),
            new_value=not original_value,
        )
        adm = await repo.select_adm_id(int(data[3]))
        await callback_query.message.edit_reply_markup(
            reply_markup=await create_kb.create_rights(adm)
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("delete_admin_check_"))
async def delete_admin_check(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="Да", callback_data=f"delete_admin_{data[3]}"))
        kb.row(InlineKeyboardButton(text="Назад", callback_data=f"admin_list"))
        await callback_query.message.edit_text(
            "Выберите админа:", reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data.startswith("delete_admin_"))
async def delete_admin(callback_query: CallbackQuery):
    try:
        data = callback_query.data.split("_")
        adm = await repo.delete(int(data[2]))
        adm_list = await repo.select_all()
        await callback_query.message.edit_text(
            "Выберите админа:", reply_markup=await create_kb.create_adm_list(adm_list)
        )
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data == "update_channel_link")
async def update_channel_link_prompt(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.edit_text("Введите новую ссылку на канал:")
        await state.set_state(Admin.update_channel_link)
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.message(Admin.update_channel_link)
async def update_channel_link_handler(message: Message, state: FSMContext):
    try:
        new_link = message.text.strip()
        if not new_link:
            await message.answer("Ссылка не может быть пустой.")
            return

        # Загружаем переменные окружения из файла .env
        load_dotenv()

        # Обновляем значение переменной в файле .env
        set_key(".env", "CHANNEL__LINK", str(new_link))

        # Обновляем значение переменной в текущем окружении
        os.environ["CHANNEL__LINK"] = str(new_link)
        reload_settings()

        # Перезапуск планировщика с новыми настройками
        from utils.shedule import restart_scheduler
        await restart_scheduler()

        await message.answer(f"Ссылка на канал успешно обновлена: {new_link}")
        await state.clear()
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")


@admin_router.callback_query(F.data == "admin_add_account")
async def get_session_file_chat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Admin.add_account)
    await callback.message.answer("Пришлите файл сессии телетон")


@admin_router.message(F.document, Admin.add_account)
async def get_session_file_chat(message: Message):
    document = message.document

    # Проверка расширения файла
    if not document.file_name.endswith(".session"):
        await message.answer("⚠️ Файл должен иметь расширение `.session`.")
        return

    # Создание папки accounts, если не существует
    os.makedirs(ACCOUNTS_DIR, exist_ok=True)

    # Полный путь к файлу
    session_path = os.path.join(ACCOUNTS_DIR, document.file_name)

    # Скачивание и сохранение файла
    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, destination=session_path)

    # Логируем добавление
    await account_manager.log_to_chat(
        f"📱 New account added: {document.file_name} | Total files: {len(account_manager.get_account_list())}",
        "SUCCESS"
    )

    await message.answer(f"✅ Файл сессии `{document.file_name}` успешно сохранён в папку `accounts/`.")