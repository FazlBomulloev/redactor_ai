from datetime import datetime
from functools import wraps

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from core.repositories import ThematicBlockRepository
from core.repositories.admin import AdminRepository
from core.repositories.publication import PublicationRepository
from core.repositories.publication_schedule import PublicationScheduleRepository
from core.repositories.folder import FolderRepository
from utils.adm import check_permission, super_adm
from utils.create_keyboard import create_kb
from utils.shedule import update_scheduler

publication_schedule_router = Router()
repo = PublicationScheduleRepository()
repo_pb = PublicationRepository()
repo_fold = FolderRepository()
repo_block = ThematicBlockRepository()
repo_adm = AdminRepository()


class AddTime(StatesGroup):
    time = State()
    tb = State()
    today: int
    time_in_pb: str


class EditPb(StatesGroup):
    id = State()
    value = State()
    column: str
    tb = State()


class Pub(StatesGroup):
    id = State()


@publication_schedule_router.callback_query(F.data == "publication_schedule")
@check_permission("publication")
async def publication_schedule_menu(callback_query: CallbackQuery):
    try:
        await callback_query.message.edit_text(
            "Расписание публикаций", reply_markup=await create_kb.create_ps()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


# Заменить функцию publication_data в routers/publication_schedule.py

@publication_schedule_router.callback_query(F.data.startswith("ps_"))
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        data = callback_query.data.split("_")
        list_pb = await repo.select_all()
        page = int(data[2]) if len(data) > 2 else 0
        page_size = 20

        # Сохраняем тип дня в состоянии
        if data[1] == "weekday":
            add_time_today = 0
            await state.update_data(add_time_today=0)
            filtered_pb = [pb for pb in list_pb if pb.today < 5]
        elif data[1] == "weekend":
            add_time_today = 5
            await state.update_data(add_time_today=5)
            filtered_pb = [pb for pb in list_pb if pb.today > 4]
        else:
            await callback_query.message.answer("Неверный формат данных.")
            return

        # ⬇️ СОРТИРОВКА ПО ВРЕМЕНИ
        try:
            filtered_pb.sort(key=lambda pb: datetime.strptime(pb.time, "%H:%M"))
        except Exception as e:
            print(f"Ошибка при сортировке публикаций: {e}")

        total_pages = (len(filtered_pb) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_pb = filtered_pb[start_idx:end_idx]

        for pb in current_page_pb:
            if not pb.thematic_block_id and not pb.ind_pub_id:
                continue

            if isinstance(pb.thematic_block_id, int):
                block_ids = [str(pb.thematic_block_id)]
            else:
                block_ids = pb.thematic_block_id.split(",") if pb.thematic_block_id else []

            block_ids = [id.strip() for id in block_ids if id.strip()]
            
            # Показываем время даже если нет ТБ (пустое время)
            if not block_ids or block_ids == ['0'] or '0' in block_ids:
                tx = "Пустое время"
            else:
                try:
                    blocks = await repo_block.select_id(block_ids)
                    if blocks:
                        # Проверяем на None в каждом блоке
                        block_names = []
                        for block in blocks:
                            if block and hasattr(block, 'name') and block.name:
                                block_names.append(block.name)
                            else:
                                block_names.append("Неизвестный блок")
                        tx = ", ".join(block_names) if block_names else "Неизвестные блоки"
                    else:
                        tx = "Блоки не найдены"
                except Exception as e:
                    print(f"Error getting blocks: {e}")
                    tx = "Ошибка загрузки блоков"
                
                # Если текст пустой, проверяем индивидуальную публикацию
                if (not tx or tx in ["Блоки не найдены", "Ошибка загрузки блоков"]) and pb.ind_pub_id and pb.ind_pub_id != 0:
                    try:
                        pub = await repo_pb.select_id(pb.ind_pub_id)
                        if pub and hasattr(pub, 'name') and pub.name:
                            tx = pub.name
                        else:
                            tx = "Неизвестная публикация"
                    except Exception as e:
                        print(f"Error getting publication: {e}")
                        tx = "Ошибка загрузки публикации"
                    
            btn = InlineKeyboardButton(
                text=f"{pb.time} || {tx}",
                callback_data=f"pb_{pb.id}",
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"ps_{data[1]}_{page - 1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"ps_{data[1]}_{page + 1}"
                )
                kb.row(btn_next)

        btn_add_time = InlineKeyboardButton(
            text="Добавить время", callback_data="add_time"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_add_time)
        kb.row(btn_back)

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = "Публикации:"
        new_markup = kb.as_markup()

        if current_text != new_text or current_markup != new_markup:
            await callback_query.message.edit_text(new_text, reply_markup=new_markup)
            # Обновляем планировщик после изменения времени
            await update_scheduler()
        await state.set_state(Pub.id)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


# Заменить функцию publication_detail в routers/publication_schedule.py

@publication_schedule_router.callback_query(F.data.startswith("pb_"))
async def publication_detail(callback_query: CallbackQuery, state: FSMContext):
    try:
        pb_id = callback_query.data.split("_")[1]
        pb = await repo.select_id(pb_id)

        if not pb:
            await callback_query.message.answer("Запись расписания не найдена.")
            return

        if not pb.thematic_block_id and not pb.ind_pub_id:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        if isinstance(pb.thematic_block_id, int):
            block_ids = [str(pb.thematic_block_id)]
        else:
            block_ids = pb.thematic_block_id.split(",") if pb.thematic_block_id else []

        block_ids = [id.strip() for id in block_ids if id.strip()]
        
        kb = InlineKeyboardBuilder()
        btn_edit_time = InlineKeyboardButton(
            text="Изменить время", callback_data=f"changepb_edit_time_{pb_id}"
        )
        btn_edit_tb = InlineKeyboardButton(
            text="Изменить блок", callback_data=f"changepb_edit_tb_{pb_id}"
        )
        btn_delete_tb = InlineKeyboardButton(
            text="Удалить", callback_data=f"changepb_delete_{pb_id}"
        )
        btn_delete_single_tb = InlineKeyboardButton(
            text="Удалить блок", callback_data=f"delete_single_tb_{pb_id}"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        
        if (isinstance(pb.thematic_block_id, int) and pb.thematic_block_id == 0) or \
                (isinstance(pb.thematic_block_id, str) and ('0' in pb.thematic_block_id.split(',') or pb.thematic_block_id.strip() == '')):

            if callback_query.from_user.id in super_adm:
                kb.row(btn_edit_time)
                kb.row(btn_delete_tb)
            kb.row(btn_back)
        else:
            if callback_query.from_user.id in super_adm:
                kb.row(btn_edit_time)
                kb.row(btn_delete_tb)
            kb.row(btn_edit_tb)
            kb.row(btn_delete_single_tb)
            kb.row(btn_back)
            
        # Показываем информацию о блоках или пустом времени
        if not block_ids or block_ids == ['0'] or '0' in block_ids:
            block_names = "Пустое время"
        else:
            try:
                blocks = await repo_block.select_id(block_ids)
                if blocks:
                    # Проверяем на None в каждом блоке
                    block_names_list = []
                    for block in blocks:
                        if block and hasattr(block, 'name') and block.name:
                            block_names_list.append(block.name)
                        else:
                            block_names_list.append("Неизвестный блок")
                    block_names = ", ".join(block_names_list) if block_names_list else "Неизвестные блоки"
                else:
                    block_names = "Блоки не найдены"
            except Exception as e:
                print(f"Error getting blocks: {e}")
                block_names = "Ошибка загрузки блоков"
            
            # Если блоки не найдены, проверяем индивидуальную публикацию
            if block_names in ["Блоки не найдены", "Ошибка загрузки блоков"] and pb.ind_pub_id and pb.ind_pub_id != 0:
                try:
                    pub = await repo_pb.select_id(pb.ind_pub_id)
                    if pub and hasattr(pub, 'name') and pub.name:
                        block_names = pub.name
                    else:
                        block_names = "Неизвестная публикация"
                except Exception as e:
                    print(f"Error getting publication: {e}")
                    block_names = "Ошибка загрузки публикации"
                
        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = f"{pb.time} || {block_names}\n"
        new_markup = kb.as_markup()

        if current_text != new_text or current_markup != new_markup:
            await callback_query.message.edit_text(new_text, reply_markup=new_markup)
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("pb_"))
async def publication_detail(callback_query: CallbackQuery, state: FSMContext):
    try:
        pb_id = callback_query.data.split("_")[1]
        pb = await repo.select_id(pb_id)

        if not pb.thematic_block_id and not pb.ind_pub_id:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        if isinstance(pb.thematic_block_id, int):
            block_ids = [str(pb.thematic_block_id)]
        else:
            block_ids = pb.thematic_block_id.split(",")

        block_ids = [id.strip() for id in block_ids if id.strip()]
        
        kb = InlineKeyboardBuilder()
        btn_edit_time = InlineKeyboardButton(
            text="Изменить время", callback_data=f"changepb_edit_time_{pb_id}"
        )
        btn_edit_tb = InlineKeyboardButton(
            text="Изменить блок", callback_data=f"changepb_edit_tb_{pb_id}"
        )
        btn_delete_tb = InlineKeyboardButton(
            text="Удалить", callback_data=f"changepb_delete_{pb_id}"
        )
        btn_delete_single_tb = InlineKeyboardButton(
            text="Удалить блок", callback_data=f"delete_single_tb_{pb_id}"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        
        if (isinstance(pb.thematic_block_id, int) and pb.thematic_block_id == 0) or \
                (isinstance(pb.thematic_block_id, str) and ('0' in pb.thematic_block_id.split(',') or pb.thematic_block_id.strip() == '')):

            if callback_query.from_user.id in super_adm:
                kb.row(btn_edit_time)
                kb.row(btn_delete_tb)
            kb.row(btn_back)
        else:
            if callback_query.from_user.id in super_adm:
                kb.row(btn_edit_time)
                kb.row(btn_delete_tb)
            kb.row(btn_edit_tb)
            kb.row(btn_delete_single_tb)
            kb.row(btn_back)
            
        # Показываем информацию о блоках или пустом времени
        if not block_ids or block_ids == ['0']:
            block_names = "Пустое время"
        else:
            blocks = await repo_block.select_id(block_ids)
            block_names = ", ".join([block.name for block in blocks])
            if block_names == "" or block_names is None:
                block_names = await repo_pb.select_id(pb.ind_pub_id)
                block_names = block_names.name if block_names else "Неизвестно"
                
        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = f"{pb.time} || {block_names}\n"
        new_markup = kb.as_markup()

        if current_text != new_text or current_markup != new_markup:
            await callback_query.message.edit_text(new_text, reply_markup=new_markup)
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("changepb_"))
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        data = callback_query.data.split("_")
        if "delete" not in data:
            EditPb.column = data[2]
            EditPb.id = data[3]
        else:
            btn_back = InlineKeyboardButton(
                text="Назад", callback_data="publication_schedule"
            )
            kb.row(btn_back)
            # Очищаем тематические блоки, но оставляем время (устанавливаем в "0")
            await repo.update(int(data[2]), "thematic_block_id", "0")
            await repo.update(int(data[2]), "ind_pub_id", 0)

            current_text = callback_query.message.text
            current_markup = callback_query.message.reply_markup
            new_text = "Тематические блоки удалены, время сохранено"
            new_markup = kb.as_markup()

            if current_text != new_text or current_markup != new_markup:
                await callback_query.message.edit_text(
                    new_text, reply_markup=new_markup
                )
            await update_scheduler()
            await state.clear()
            return

        if "tb" in data:
            list_tb = await repo_block.select_all()
            page = 0  # Начальная страница
            page_size = 20

            total_pages = (len(list_tb) + page_size - 1) // page_size
            start_idx = page * page_size
            end_idx = start_idx + page_size
            current_page_pb = list_tb[start_idx:end_idx]

            for pb in current_page_pb:
                btn = InlineKeyboardButton(
                    text=f"{pb.name}", callback_data=f"select_block_{pb.id}"
                )
                kb.row(btn)

            if total_pages > 1:
                if page > 0:
                    btn_prev = InlineKeyboardButton(
                        text="<< Назад", callback_data=f"blocks_{page - 1}"
                    )
                    kb.row(btn_prev)
                if page < total_pages - 1:
                    btn_next = InlineKeyboardButton(
                        text="Вперед >>", callback_data=f"blocks_{page + 1}"
                    )
                    kb.row(btn_next)

            btn_done = InlineKeyboardButton(
                text="Готово", callback_data="done_selecting_blocks"
            )
            btn_back_folders = InlineKeyboardButton(
                text="📁 Назад к папкам", callback_data="back_to_folders"
            )
            btn_back = InlineKeyboardButton(
                text="Назад", callback_data="publication_schedule"
            )
            kb.row(btn_done)
            kb.row(btn_back_folders)
            kb.row(btn_back)

            current_text = callback_query.message.text
            current_markup = callback_query.message.reply_markup
            new_text = "Выберите блок(и):"
            new_markup = kb.as_markup()

            if current_text != new_text or current_markup != new_markup:
                await callback_query.message.edit_text(
                    new_text, reply_markup=new_markup
                )
            # Устанавливаем режим редактирования
            EditPb.tb = "edit"
            await state.update_data(edit_mode="edit", edit_id=EditPb.id)
        else:
            await callback_query.message.answer("Введите новое значение")
            await state.set_state(EditPb.value)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.message(EditPb.value)
async def publication_data(message: Message, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        if EditPb.column == "tb":
            EditPb.column = "thematic_block_id"
        await repo.update(int(EditPb.id), EditPb.column, message.text)
        await state.clear()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.add(btn_back)
        await message.answer("Изменено", reply_markup=kb.as_markup())
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("add_time"))
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.answer("Введите время чч:мм")
        await state.set_state(AddTime.time)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.message(AddTime.time)
async def publication_data(message: Message, state: FSMContext):
    try:
        await state.update_data(time=message.text)
        AddTime.time_in_pb = message.text

        kb = InlineKeyboardBuilder()

        # Добавляем кнопку для создания времени без ТБ
        btn_empty = InlineKeyboardButton(
            text="⏰ Создать время без ТБ", callback_data="create_empty_time"
        )
        kb.row(btn_empty)

        list_fold = await repo_fold.select_all()
        for fl in list_fold:
            btn = InlineKeyboardButton(
                text=f"{fl.name}", callback_data=f"select_folder_{fl.id}"
            )
            kb.row(btn)

        btn_pub = InlineKeyboardButton(
            text=f"Публикации", callback_data=f"select_publications_fl"
        )
        kb.row(btn_pub)

        await message.answer("Выберите папку или создайте пустое время:", reply_markup=kb.as_markup())

    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "create_empty_time")
async def create_empty_time(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        time = data.get("time")
        add_time_today = data.get("add_time_today", 0)

        # Создаем время без тематических блоков (устанавливаем "0")
        await repo.add(time, "0", add_time_today, 0)

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_back)

        await callback_query.message.edit_text(
            f"Время {time} создано без тематических блоков",
            reply_markup=kb.as_markup()
        )
        await update_scheduler()
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "back_to_folders")
async def back_to_folders(callback_query: CallbackQuery, state: FSMContext):
    try:
        kb = InlineKeyboardBuilder()
        
        list_fold = await repo_fold.select_all()
        for fl in list_fold:
            btn = InlineKeyboardButton(
                text=f"{fl.name}", callback_data=f"select_folder_{fl.id}"
            )
            kb.row(btn)
        
        btn_pub = InlineKeyboardButton(
            text=f"Публикации", callback_data=f"select_publications_fl"
        )
        kb.row(btn_pub)
        
        await callback_query.message.edit_text("Выберите папку:", reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@publication_schedule_router.callback_query(F.data.startswith("select_folder_"))
async def sel_folder(callback_query: CallbackQuery, state: FSMContext):
    try:
        list_pb = await repo_block.select_id_folder(callback_query.data.split("_")[2])
        page = 0  # Начальная страница
        page_size = 20

        total_pages = (len(list_pb) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_pb = list_pb[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for pb in current_page_pb:
            btn = InlineKeyboardButton(
                text=f"{pb.name}", callback_data=f"select_block_{pb.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"blocks_{page - 1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"blocks_{page + 1}"
                )
                kb.row(btn_next)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_selecting_blocks"
        )
        btn_all_folders = InlineKeyboardButton(
            text="📁 Все папки", callback_data="select_all_folders"
        )
        btn_back_folders = InlineKeyboardButton(
            text="📁 Назад к папкам", callback_data="back_to_folders"
        )
        kb.row(btn_all_folders)
        kb.row(btn_back_folders)
        kb.row(btn_done)

        await callback_query.message.edit_text(
            "Выберите блок(и):", reply_markup=kb.as_markup()
        )
        await state.set_state(AddTime.tb)
        EditPb.tb = "add"
    except Exception as e:
        await callback_query.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "select_all_folders")
async def select_all_folders(callback_query: CallbackQuery, state: FSMContext):
    try:
        list_fold = await repo_fold.select_all()

        kb = InlineKeyboardBuilder()
        for fl in list_fold:
            btn = InlineKeyboardButton(
                text=f"{fl.name}", callback_data=f"select_folder_{fl.id}"
            )
            kb.row(btn)

        btn_pub = InlineKeyboardButton(
            text=f"Публикации", callback_data=f"select_publications_fl"
        )
        kb.row(btn_pub)

        await callback_query.message.edit_text("Выберите папку:", reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.answer(f"Ошибка: {e}")


@publication_schedule_router.callback_query(F.data.startswith("blocks_"))
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        page = int(callback_query.data.split("_")[1])
        list_pb = await repo_block.select_all()
        page_size = 20

        total_pages = (len(list_pb) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_pb = list_pb[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for pb in current_page_pb:
            btn = InlineKeyboardButton(
                text=f"{pb.name}", callback_data=f"select_block_{pb.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"blocks_{page - 1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"blocks_{page + 1}"
                )
                kb.row(btn_next)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_selecting_blocks"
        )
        btn_back_folders = InlineKeyboardButton(
            text="📁 Назад к папкам", callback_data="back_to_folders"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_done)
        kb.row(btn_back_folders)
        kb.row(btn_back)

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = "Выберите блок(и):"
        new_markup = kb.as_markup()

        if current_text != new_text or current_markup != new_markup:
            await callback_query.message.edit_text(new_text, reply_markup=new_markup)
        await state.set_state(AddTime.tb)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("select_block_"))
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        block_id = callback_query.data.split("_")[2]
        current_data = await state.get_data()
        selected_blocks = current_data.get("selected_blocks", [])
        selected_blocks.append(block_id)
        await state.update_data(selected_blocks=selected_blocks)

        list_pb = await repo_block.select_all()
        page = 0  # Начальная страница
        page_size = 20

        total_pages = (len(list_pb) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_pb = list_pb[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for pb in current_page_pb:
            btn = InlineKeyboardButton(
                text=f"{pb.name}", callback_data=f"select_block_{pb.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"blocks_{page - 1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"blocks_{page + 1}"
                )
                kb.row(btn_next)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_selecting_blocks"
        )
        btn_back_folders = InlineKeyboardButton(
            text="📁 Назад к папкам", callback_data="back_to_folders"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_done)
        kb.row(btn_back_folders)
        kb.row(btn_back)

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = "Выберите блок(и):"
        new_markup = kb.as_markup()

        await state.set_state(AddTime.tb)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "done_selecting_blocks")
async def publication_data(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        selected_blocks = data.get("selected_blocks", [])
        time = data.get("time")
        add_time_today = data.get("add_time_today", 0)
        edit_mode = data.get("edit_mode")
        edit_id = data.get("edit_id")

        # Объединяем выбранные блоки в одну строку через запятую
        selected_blocks_str = ",".join(selected_blocks) if selected_blocks else "0"

        # Проверка режима работы
        if edit_mode == "edit" and edit_id:
            # При редактировании обновляем существующую запись
            await repo.update(int(edit_id), "thematic_block_id", selected_blocks_str)
            new_text = f"Вы изменили ТБ на {selected_blocks_str}"
        elif time is not None:
            # При добавлении создаем новую запись
            await repo.add(time, selected_blocks_str, add_time_today)
            new_text = f"Вы установили ТБ {selected_blocks_str} на {time}"
        else:
            await callback_query.message.answer("Ошибка: не удалось определить операцию")
            return

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_back)

        new_reply_markup = kb.as_markup()

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup

        if current_text != new_text or current_markup != new_reply_markup:
            await callback_query.message.edit_text(
                new_text, reply_markup=new_reply_markup
            )
        # Обновляем планировщик после изменений
        await update_scheduler()
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("delete_single_tb_"))
async def delete_single_tb(callback_query: CallbackQuery, state: FSMContext):
    try:
        pb_id = callback_query.data.split("_")[3]
        await state.update_data(pb_id=pb_id)  # Сохраняем pb_id в состоянии

        pb = await repo.select_id(pb_id)

        if not pb.thematic_block_id:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        if isinstance(pb.thematic_block_id, int):
            block_ids = [str(pb.thematic_block_id)]
        else:
            block_ids = pb.thematic_block_id.split(",")

        block_ids = [id.strip() for id in block_ids if id.strip()]
        if not block_ids:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        blocks = await repo_block.select_id(block_ids)
        kb = InlineKeyboardBuilder()

        for block in blocks:
            btn = InlineKeyboardButton(
                text=f"{block.name}",
                callback_data=f"select_delete_block_{pb_id}_{block.id}",
            )
            kb.row(btn)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_deleting_blocks"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_done)
        kb.row(btn_back)

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = "Выберите блок(и) для удаления:"
        new_markup = kb.as_markup()

        if current_text != new_text or current_markup != new_markup:
            await callback_query.message.edit_text(new_text, reply_markup=new_markup)
        await state.set_state(EditPb.tb)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("select_delete_block_"))
async def select_delete_block(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = callback_query.data.split("_")
        pb_id = data[3]
        block_id = data[4]

        current_data = await state.get_data()
        selected_blocks = current_data.get("selected_blocks", [])
        selected_blocks.append(int(block_id))
        await state.update_data(selected_blocks=selected_blocks)

        pb = await repo.select_id(pb_id)
        if not pb.thematic_block_id:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        if isinstance(pb.thematic_block_id, int):
            block_ids = [str(pb.thematic_block_id)]
        else:
            block_ids = pb.thematic_block_id.split(",")

        block_ids = [id.strip() for id in block_ids if id.strip()]
        if not block_ids:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        blocks = await repo_block.select_id(block_ids)
        kb = InlineKeyboardBuilder()

        for block in blocks:
            btn = InlineKeyboardButton(
                text=f"{block.name}",
                callback_data=f"select_delete_block_{pb_id}_{block.id}",
            )
            kb.row(btn)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_deleting_blocks"
        )
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_done)
        kb.row(btn_back)

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup
        new_text = "Выберите блок(и) для удаления:"
        new_markup = kb.as_markup()

        await state.set_state(EditPb.tb)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "done_deleting_blocks")
async def done_deleting_blocks(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        selected_blocks = data.get("selected_blocks", [])
        pb_id = data.get("pb_id")  # Получаем pb_id из состояния

        if pb_id is None:
            await callback_query.message.answer("Ошибка: pb_id не найден.")
            return

        pb = await repo.select_id(pb_id)
        if not pb.thematic_block_id:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        if isinstance(pb.thematic_block_id, int):
            block_ids = [str(pb.thematic_block_id)]
        else:
            block_ids = pb.thematic_block_id.split(",")

        block_ids = [id.strip() for id in block_ids if id.strip()]
        if not block_ids:
            await callback_query.message.answer("Тематический блок не найден.")
            return

        for block_id in selected_blocks:
            if str(block_id) in block_ids:
                block_ids.remove(str(block_id))

        # Если не осталось блоков, устанавливаем "0" вместо пустой строки
        new_block_ids_str = ",".join(block_ids) if block_ids else "0"
        await repo.update(int(pb_id), "thematic_block_id", new_block_ids_str)

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_back)

        new_text = f"Тематические блоки {', '.join(map(str, selected_blocks))} удалены."
        new_reply_markup = kb.as_markup()

        current_text = callback_query.message.text
        current_markup = callback_query.message.reply_markup

        if current_text != new_text or current_markup != new_reply_markup:
            await callback_query.message.edit_text(
                new_text, reply_markup=new_reply_markup
            )
        # Обновляем планировщик после изменений
        await update_scheduler()
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("select_publications_fl"))
async def select_publications_fl(callback_query: CallbackQuery, state: FSMContext):
    try:
        list_pb = await repo_pb.select_all()
        page = 0
        page_size = 20

        total_pages = (len(list_pb) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_pb = list_pb[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for pb in current_page_pb:
            btn = InlineKeyboardButton(
                text=f"{pb.name}", callback_data=f"select_publication_{pb.id}"
            )
            kb.row(btn)

        if total_pages > 1:
            if page > 0:
                btn_prev = InlineKeyboardButton(
                    text="<< Назад", callback_data=f"publications_{page - 1}"
                )
                kb.row(btn_prev)
            if page < total_pages - 1:
                btn_next = InlineKeyboardButton(
                    text="Вперед >>", callback_data=f"publications_{page + 1}"
                )
                kb.row(btn_next)

        btn_done = InlineKeyboardButton(
            text="Готово", callback_data="done_selecting_publications"
        )
        btn_back_folders = InlineKeyboardButton(
            text="📁 Назад к папкам", callback_data="back_to_folders"
        )
        kb.row(btn_done)
        kb.row(btn_back_folders)

        await callback_query.message.edit_text(
            "Выберите публикацию:", reply_markup=kb.as_markup()
        )
        await state.set_state(AddTime.tb)
        EditPb.tb = "add"
    except Exception as e:
        await callback_query.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data.startswith("select_publication_"))
async def select_publication(callback_query: CallbackQuery, state: FSMContext):
    try:
        pub_id = callback_query.data.split("_")[2]
        current_data = await state.get_data()
        selected_publications = current_data.get("selected_publications", [])
        selected_publications.append(pub_id)
        await state.update_data(selected_publications=selected_publications)

        await callback_query.answer(f"Публикация {pub_id} выбрана")
    except Exception as e:
        await callback_query.answer(f"Ошибка: {str(e)}")


@publication_schedule_router.callback_query(F.data == "done_selecting_publications")
async def done_selecting_publications(callback_query: CallbackQuery, state: FSMContext):
    try:
        data = await state.get_data()
        selected_publications = data.get("selected_publications", [])
        time = data.get("time")
        add_time_today = data.get("add_time_today", 0)

        if selected_publications:
            # Для публикаций используем ind_pub_id
            pub_id = selected_publications[0]  # Берем первую выбранную публикацию
            await repo.add(time, "0", add_time_today, int(pub_id))
            new_text = f"Вы установили публикацию на {time}"
        else:
            new_text = "Публикация не выбрана"

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(
            text="Назад", callback_data="publication_schedule"
        )
        kb.row(btn_back)

        await callback_query.message.edit_text(
            new_text, reply_markup=kb.as_markup()
        )
        await update_scheduler()
        await state.clear()
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {str(e)}")