from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.repositories.ai_config import AIApiKeyRepository, AIAgentRepository
from utils.adm import super_adm
from utils.ai_manager import ai_manager

ai_admin_router = Router()
api_key_repo = AIApiKeyRepository()
agent_repo = AIAgentRepository()


class AIApiKeyStates(StatesGroup):
    name = State()
    api_key = State()
    description = State()


class AIAgentStates(StatesGroup):
    name = State()
    agent_id = State()
    description = State()
    api_key_id = State()


@ai_admin_router.callback_query(F.data == "ai_management")
async def ai_management_menu(callback_query: CallbackQuery):
    """Главное меню управления ИИ"""
    try:
        if callback_query.from_user.id not in super_adm:
            await callback_query.message.answer("У вас нет прав для управления ИИ настройками.")
            return
        
        kb = InlineKeyboardBuilder()
        btn_api_keys = InlineKeyboardButton(text="🔑 API Ключи", callback_data="ai_api_keys")
        btn_agents = InlineKeyboardButton(text="🤖 ИИ Агенты", callback_data="ai_agents")
        btn_reload = InlineKeyboardButton(text="🔄 Перезагрузить", callback_data="ai_reload_config")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="administration")
        
        kb.row(btn_api_keys)
        kb.row(btn_agents)
        kb.row(btn_reload)
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "Управление ИИ настройками:", 
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data == "ai_reload_config")
async def reload_ai_config(callback_query: CallbackQuery):
    """Перезагрузка конфигурации ИИ"""
    try:
        if callback_query.from_user.id not in super_adm:
            await callback_query.message.answer("У вас нет прав для этого действия.")
            return
        
        await ai_manager.reload_configuration()
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_management")
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "✅ Конфигурация ИИ успешно перезагружена!",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


# ========== УПРАВЛЕНИЕ API КЛЮЧАМИ ==========

@ai_admin_router.callback_query(F.data == "ai_api_keys")
async def ai_api_keys_menu(callback_query: CallbackQuery):
    """Меню управления API ключами"""
    try:
        api_keys = await api_key_repo.get_all_with_agents()
        
        kb = InlineKeyboardBuilder()
        
        if api_keys:
            for key in api_keys:
                agent_count = len(key.agents) if key.agents else 0
                btn = InlineKeyboardButton(
                    text=f"{key.name} ({agent_count} агентов)",
                    callback_data=f"ai_key_detail_{key.id}"
                )
                kb.row(btn)
        
        btn_add = InlineKeyboardButton(text="➕ Добавить API ключ", callback_data="ai_add_api_key")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_management")
        
        kb.row(btn_add)
        kb.row(btn_back)
        
        text = f"🔑 API Ключи ({len(api_keys)} шт.):\n\n"
        if not api_keys:
            text += "Нет добавленных API ключей."
        
        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data == "ai_add_api_key")
async def add_api_key_start(callback_query: CallbackQuery, state: FSMContext):
    """Начало добавления API ключа"""
    try:
        await callback_query.message.answer("Введите название для API ключа:")
        await state.set_state(AIApiKeyStates.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIApiKeyStates.name)
async def add_api_key_name(message: Message, state: FSMContext):
    """Получение названия API ключа"""
    try:
        await state.update_data(name=message.text.strip())
        await message.answer("Введите API ключ:")
        await state.set_state(AIApiKeyStates.api_key)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIApiKeyStates.api_key)
async def add_api_key_key(message: Message, state: FSMContext):
    """Получение API ключа"""
    try:
        await state.update_data(api_key=message.text.strip())
        await message.answer("Введите описание (или '-' чтобы пропустить):")
        await state.set_state(AIApiKeyStates.description)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIApiKeyStates.description)
async def add_api_key_description(message: Message, state: FSMContext):
    """Сохранение API ключа"""
    try:
        data = await state.get_data()
        description = message.text.strip() if message.text.strip() != "-" else ""
        
        await api_key_repo.add(
            name=data['name'],
            api_key=data['api_key'], 
            description=description
        )
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="К API ключам", callback_data="ai_api_keys")
        kb.row(btn_back)
        
        await message.answer(
            f"✅ API ключ '{data['name']}' успешно добавлен!",
            reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_key_detail_"))
async def api_key_detail(callback_query: CallbackQuery):
    """Детали API ключа"""
    try:
        key_id = int(callback_query.data.split("_")[3])
        api_keys = await api_key_repo.get_all_with_agents()
        api_key = next((k for k in api_keys if k.id == key_id), None)
        
        if not api_key:
            await callback_query.message.answer("API ключ не найден.")
            return
        
        kb = InlineKeyboardBuilder()
        
        btn_delete = InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"ai_key_delete_confirm_{key_id}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_api_keys")
        
        kb.row(btn_delete)
        kb.row(btn_back)
        
        masked_key = api_key.api_key[:8] + "..." + api_key.api_key[-4:]
        agent_count = len(api_key.agents) if api_key.agents else 0
        
        text = f"🔑 API Ключ: {api_key.name}\n\n"
        text += f"Ключ: {masked_key}\n"
        text += f"Агентов: {agent_count}\n"
        if api_key.description:
            text += f"Описание: {api_key.description}\n"
        
        if api_key.agents:
            text += f"\n🤖 Привязанные агенты:\n"
            for agent in api_key.agents:
                text += f"• {agent.name}\n"
        
        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_key_delete_confirm_"))
async def delete_api_key_confirm(callback_query: CallbackQuery):
    """Подтверждение удаления API ключа"""
    try:
        key_id = int(callback_query.data.split("_")[4])
        api_key = await api_key_repo.select_id(key_id)
        
        if not api_key:
            await callback_query.message.answer("API ключ не найден.")
            return
        
        kb = InlineKeyboardBuilder()
        btn_confirm = InlineKeyboardButton(
            text="⚠️ Да, удалить",
            callback_data=f"ai_key_delete_{key_id}"
        )
        btn_cancel = InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"ai_key_detail_{key_id}"
        )
        
        kb.row(btn_confirm)
        kb.row(btn_cancel)
        
        await callback_query.message.edit_text(
            f"⚠️ Вы действительно хотите удалить API ключ '{api_key.name}'?\n\n"
            "❗ Это также удалит ВСЕ привязанные агенты!\n"
            "Это действие нельзя отменить!",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_key_delete_"))
async def delete_api_key(callback_query: CallbackQuery):
    """Удаление API ключа"""
    try:
        key_id = int(callback_query.data.split("_")[3])
        await api_key_repo.delete_key(key_id)
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="К API ключам", callback_data="ai_api_keys")
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "✅ API ключ и все связанные агенты успешно удалены!",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


# ========== УПРАВЛЕНИЕ АГЕНТАМИ ==========

@ai_admin_router.callback_query(F.data == "ai_agents")
async def ai_agents_menu(callback_query: CallbackQuery):
    """Меню управления ИИ агентами"""
    try:
        agents = await agent_repo.get_all_with_api_keys()
        
        kb = InlineKeyboardBuilder()
        
        if agents:
            for agent in agents:
                api_key_name = agent.api_key.name if agent.api_key else "Без ключа"
                btn = InlineKeyboardButton(
                    text=f"{agent.name} ({api_key_name})",
                    callback_data=f"ai_agent_detail_{agent.id}"
                )
                kb.row(btn)
        
        btn_add = InlineKeyboardButton(text="➕ Добавить агента", callback_data="ai_add_agent")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_management")
        
        kb.row(btn_add)
        kb.row(btn_back)
        
        text = f"🤖 ИИ Агенты ({len(agents)} шт.):\n\n"
        if not agents:
            text += "Нет добавленных агентов."
        
        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data == "ai_add_agent")
async def add_agent_start(callback_query: CallbackQuery, state: FSMContext):
    """Начало добавления агента - выбор API ключа"""
    try:
        api_keys = await api_key_repo.select_all()
        if not api_keys:
            await callback_query.message.answer("❌ Сначала добавьте API ключ!")
            return
        
        kb = InlineKeyboardBuilder()
        for key in api_keys:
            btn = InlineKeyboardButton(
                text=key.name,
                callback_data=f"ai_select_api_key_{key.id}"
            )
            kb.row(btn)
        
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_agents")
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "Выберите API ключ для нового агента:",
            reply_markup=kb.as_markup()
        )
        await state.set_state(AIAgentStates.api_key_id)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_select_api_key_"))
async def select_api_key_for_agent(callback_query: CallbackQuery, state: FSMContext):
    """Выбор API ключа и переход к вводу названия агента"""
    try:
        api_key_id = int(callback_query.data.split("_")[4])
        await state.update_data(api_key_id=api_key_id)
        
        await callback_query.message.answer("Введите название для агента:")
        await state.set_state(AIAgentStates.name)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIAgentStates.name)
async def add_agent_name(message: Message, state: FSMContext):
    """Получение названия агента"""
    try:
        await state.update_data(name=message.text.strip())
        await message.answer("Введите ID агента (например: ag:xxx:xxx:xxx:xxx):")
        await state.set_state(AIAgentStates.agent_id)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIAgentStates.agent_id)
async def add_agent_id(message: Message, state: FSMContext):
    """Получение ID агента"""
    try:
        await state.update_data(agent_id=message.text.strip())
        await message.answer("Введите описание (или '-' чтобы пропустить):")
        await state.set_state(AIAgentStates.description)
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.message(AIAgentStates.description)
async def add_agent_description(message: Message, state: FSMContext):
    """Сохранение агента"""
    try:
        data = await state.get_data()
        description = message.text.strip() if message.text.strip() != "-" else ""
        
        await agent_repo.add(
            name=data['name'],
            agent_id=data['agent_id'],
            api_key_id=data['api_key_id'],
            description=description
        )
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="К агентам", callback_data="ai_agents")
        kb.row(btn_back)
        
        await message.answer(
            f"✅ Агент '{data['name']}' успешно добавлен!",
            reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_agent_detail_"))
async def agent_detail(callback_query: CallbackQuery):
    """Детали агента"""
    try:
        agent_id = int(callback_query.data.split("_")[3])
        agents = await agent_repo.get_all_with_api_keys()
        agent = next((a for a in agents if a.id == agent_id), None)
        
        if not agent:
            await callback_query.message.answer("Агент не найден.")
            return
        
        kb = InlineKeyboardBuilder()
        
        btn_delete = InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"ai_agent_delete_confirm_{agent_id}"
        )
        btn_back = InlineKeyboardButton(text="Назад", callback_data="ai_agents")
        
        kb.row(btn_delete)
        kb.row(btn_back)
        
        masked_id = agent.agent_id[:12] + "..." + agent.agent_id[-8:]
        api_key_name = agent.api_key.name if agent.api_key else "Не найден"
        
        text = f"🤖 Агент: {agent.name}\n\n"
        text += f"ID: {masked_id}\n"
        text += f"API Ключ: {api_key_name}\n"
        if agent.description:
            text += f"Описание: {agent.description}\n"
        
        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_agent_delete_confirm_"))
async def delete_agent_confirm(callback_query: CallbackQuery):
    """Подтверждение удаления агента"""
    try:
        agent_id = int(callback_query.data.split("_")[4])
        agent = await agent_repo.select_id(agent_id)
        
        if not agent:
            await callback_query.message.answer("Агент не найден.")
            return
        
        kb = InlineKeyboardBuilder()
        btn_confirm = InlineKeyboardButton(
            text="⚠️ Да, удалить",
            callback_data=f"ai_agent_delete_{agent_id}"
        )
        btn_cancel = InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"ai_agent_detail_{agent_id}"
        )
        
        kb.row(btn_confirm)
        kb.row(btn_cancel)
        
        await callback_query.message.edit_text(
            f"⚠️ Вы действительно хотите удалить агента '{agent.name}'?\n\n"
            "Это действие нельзя отменить!",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@ai_admin_router.callback_query(F.data.startswith("ai_agent_delete_"))
async def delete_agent(callback_query: CallbackQuery):
    """Удаление агента"""
    try:
        agent_id = int(callback_query.data.split("_")[3])
        await agent_repo.delete_agent(agent_id)
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="К агентам", callback_data="ai_agents")
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "✅ Агент успешно удален!",
            reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")