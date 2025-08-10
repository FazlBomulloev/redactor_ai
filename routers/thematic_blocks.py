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


def split_blocks_by_pages(blocks, page_size=20):
    """Разделяет блоки на страницы"""
    pages = []
    for i in range(0, len(blocks), page_size):
        pages.append(blocks[i:i + page_size])
    return pages


def create_safe_display_text(blocks, max_length=3500):
    """Создает безопасный текст для отображения блоков"""
    if not blocks:
        return "Нет блоков в этой папке."
    
    text_parts = []
    current_length = 0
    
    for i, block in enumerate(blocks, 1):
        # Безопасное получение имени блока
        block_name = "Неизвестный блок"
        if block and hasattr(block, 'name') and block.name:
            block_name = block.name
        
        # Безопасное получение источников
        sources = "Нет источников"
        if block and hasattr(block, 'source') and block.source:
            if isinstance(block.source, list):
                sources = ", ".join(block.source[:3])  # Показываем только первые 3
                if len(block.source) > 3:
                    sources += f" и еще {len(block.source) - 3}"
            else:
                sources_list = str(block.source).split(',')[:3]
                sources = ", ".join([s.strip() for s in sources_list])
                if ',' in str(block.source) and len(str(block.source).split(',')) > 3:
                    sources += "..."
        
        # Формируем строку для блока
        block_text = f"{i}. {block_name}\n   Источники: {sources}\n\n"
        
        # Проверяем, не превысим ли лимит
        if current_length + len(block_text) > max_length:
            break
            
        text_parts.append(block_text)
        current_length += len(block_text)
    
    return "".join(text_parts)


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
async def thematic_blocks_menu(callback_query: CallbackQuery, state: FSMContext):
    try:
        # Извлекаем имя папки и страницу
        data_parts = callback_query.data.split("_")
        fl_name = data_parts[1]
        page = int(data_parts[2]) if len(data_parts) > 2 else 0
        
        fl = await repo_fl.select_name(fl_name)
        if not fl:
            await callback_query.message.answer("Папка не найдена.")
            return
            
        CreateBlock.folder = fl
        list_blocks = await repo.select_id_folder(fl.id)
        
        # Разделяем блоки на страницы
        pages = split_blocks_by_pages(list_blocks, page_size=15)
        total_pages = len(pages) if pages else 1
        
        if page >= total_pages:
            page = 0
        
        current_page_blocks = pages[page] if pages else []
        
        # Создаем клавиатуру
        kb = InlineKeyboardBuilder()
        
        # Добавляем кнопки для блоков на текущей странице
        for block in current_page_blocks:
            block_name = "Неизвестный блок"
            callback_data = f"tb_unknown_{block.id}"  # По умолчанию используем ID
            
            if block and hasattr(block, 'name') and block.name:
                block_name = block.name
                # ИСПРАВЛЕНИЕ: используем ID вместо имени в callback_data
                callback_data = f"tb_id_{block.id}"
                
            btn = InlineKeyboardButton(
                text=block_name, 
                callback_data=callback_data
            )
            kb.row(btn)
        
        # Кнопки навигации между страницами
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад", 
                callback_data=f"fl_{fl_name}_{page - 1}"
            ))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️", 
                callback_data=f"fl_{fl_name}_{page + 1}"
            ))
        
        if nav_buttons:
            if len(nav_buttons) == 2:
                kb.row(nav_buttons[0], nav_buttons[1])
            else:
                kb.row(nav_buttons[0])
        
        # Кнопки управления папкой
        btn_change_name = InlineKeyboardButton(
            text="Изменить имя папки", 
            callback_data=f"changefl_name_{fl_name}"
        )
        btn_delete_folder = InlineKeyboardButton(
            text="Удалить папку", 
            callback_data=f"changefl_del_{fl_name}"
        )
        btn_create_block = InlineKeyboardButton(
            text="Создать блок", 
            callback_data="create_block"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", 
            callback_data="thematic_blocks"
        )
        
        kb.row(btn_change_name)
        kb.row(btn_delete_folder)
        kb.row(btn_create_block)
        kb.row(btn_back)
        
        # Формируем текст
        header = f"Папка: {fl.name}\n"
        if total_pages > 1:
            header += f"Страница {page + 1}/{total_pages}\n"
        header += f"Всего блоков: {len(list_blocks)}\n\n"
                
        await callback_query.message.edit_text(header, reply_markup=kb.as_markup())
        
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.callback_query(F.data.startswith("changefl_"))
async def thematic_blocks_menu(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split("_")
        if data[1] == "del":
            fl = await repo_fl.select_name(data[2])
            if fl:
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
        print(f"🔍 TB button clicked: {callback_query.data}")
        
        # Извлекаем данные из callback_data
        data_parts = callback_query.data.split("_", 2)
        
        if len(data_parts) < 2:
            await callback_query.message.answer("Неверный формат данных.")
            return
        
        if data_parts[1] == "id":
            block_id = int(data_parts[2])
            print(f"🔢 Processing block by ID: {block_id}")
            name_tb_obj = await repo.select_id(block_id)
            
        elif data_parts[1] == "unknown":
            
            block_id = int(data_parts[2])
            print(f"🔢 Processing unknown block by ID: {block_id}")
            name_tb_obj = await repo.select_id(block_id)
            
        else:
            
            name_tb = "_".join(data_parts[1:])  # Восстанавливаем полное имя
            print(f"📝 Processing block by name: '{name_tb}'")
            name_tb_obj = await repo.select_name(name_tb)
        
        print(f"📋 Query result: {name_tb_obj}")
        
        if not name_tb_obj:
            await callback_query.message.answer("Блок не найден в базе данных.")
            return
        
        # Безопасное формирование текста
        form_text = ""
        
        # Имя
        block_name = "Неизвестный блок"
        if hasattr(name_tb_obj, 'name') and name_tb_obj.name:
            block_name = name_tb_obj.name
        form_text += f"Название: {block_name}\n\n"
        
        # Источники
        if hasattr(name_tb_obj, 'source') and name_tb_obj.source:
            if isinstance(name_tb_obj.source, list):
                sources = "\n".join([f"• {src}" for src in name_tb_obj.source[:10]])
                if len(name_tb_obj.source) > 10:
                    sources += f"\n... и еще {len(name_tb_obj.source) - 10} источников"
            else:
                sources_list = str(name_tb_obj.source).split(',')[:10]
                sources = "\n".join([f"• {src.strip()}" for src in sources_list])
                if len(str(name_tb_obj.source).split(',')) > 10:
                    sources += "\n... (показаны первые 10)"
            form_text += f"Источники:\n{sources}\n\n"
        else:
            form_text += "Источники: не указаны\n\n"
        
        # Время
        if hasattr(name_tb_obj, 'time_back') and name_tb_obj.time_back:
            form_text += f"Время поиска: {name_tb_obj.time_back} минут\n\n"
        else:
            form_text += "Время поиска: не указано\n\n"
        
        # Стоп-слова
        if hasattr(name_tb_obj, 'stop_words') and name_tb_obj.stop_words:
            stop_words = str(name_tb_obj.stop_words)
            if len(stop_words) > 200:
                stop_words = stop_words[:197] + "..."
            form_text += f"Стоп-слова: {stop_words}\n\n"
        else:
            form_text += "Стоп-слова: не указаны\n\n"
        
        # Описание
        if hasattr(name_tb_obj, 'description') and name_tb_obj.description:
            description = str(name_tb_obj.description)
            if len(description) > 300:
                description = description[:297] + "..."
            form_text += f"Описание: {description}"
        else:
            form_text += "Описание: не указано"

        
        await callback_query.message.edit_text(
            form_text, 
            reply_markup=await create_kb.create_tb_individual_by_id(name_tb_obj.id, name_tb_obj.name)
        )
        
    except Exception as e:
        print(f"❌ Error in thematic_block handler: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
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
async def time_back_block(message: Message, state: FSMContext):
    try:
        await message.answer(
            "Введите время за которое нужно просмотреть посты в минутах"
        )
        await state.update_data(stop_words=message.text)
        await state.set_state(CreateBlock.time_back)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.time_back)
async def description_block_final(message: Message, state: FSMContext):
    try:
        await message.answer("Введите описание")
        await state.update_data(time_back=message.text)
        await state.set_state(CreateBlock.description)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(CreateBlock.description)
async def save_block(message: Message, state: FSMContext):
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
        print(f"🔧 Change request: {change}")
        
        # Определяем, используется ли новый формат с ID
        if len(change) >= 4 and change[2] == "id":
            # Новый формат: changetb_action_id_123
            action = change[1]
            block_id = int(change[3])
            
            if action == "delete":
                # Удаление по ID
                tb = await repo.select_id(block_id)
                if tb:
                    await repo.delete(tb.id)
                    await repo_pb.delete_tb_id(tb.id)
                await callback_query.message.edit_text(
                    "Удалено", reply_markup=kb.as_markup()
                )
                await state.clear()
                return
            else:
                # Подготовка к изменению
                Change.model = [change[0], action, str(block_id)]
                Change.mess_id = callback_query.message.message_id
                await callback_query.message.answer("Введите новое значение")
                await state.set_state(Change.value)
                
        else:
            # Старый формат: changetb_action_name
            Change.model = change
            if change[1] == "delete":
                tb = await repo.select_name(change[2])
                if tb:
                    await repo.delete(tb.id)
                    await repo_pb.delete_tb_id(tb.id)
                await callback_query.message.edit_text(
                    "Удалено", reply_markup=kb.as_markup()
                )
                await state.clear()
                return
            
            Change.mess_id = callback_query.message.message_id
            await callback_query.message.answer("Введите новое значение")
            await state.set_state(Change.value)
            
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@thematic_blocks_router.message(Change.value)
async def update_block_value(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="thematic_blocks"))
        await state.update_data(value=message.text)
        data = await state.get_data()
        model = Change.model
        
        print(f"🔧 Updating with model: {model}")
        
        # Обработка поля
        field = model[1]
        if field == "timeback":
            field = "time_back"
        elif field == "sw":
            field = "stop_words"
        
        # Определяем идентификатор для обновления
        if len(model) >= 3 and model[2].isdigit():
            # Обновление по ID
            block_id = int(model[2])
            await repo.update_by_id(block_id, field, data.get("value"))
        else:
            # Обновление по имени (старый способ)
            await repo.update(model[2], field, data.get("value"))

        await message.answer("Изменено", reply_markup=kb.as_markup())
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")