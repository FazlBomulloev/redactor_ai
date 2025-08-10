from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.repositories.stop_words import StopWordsRepository
from utils.adm import check_permission

stop_words_router = Router()
repo = StopWordsRepository()


class CreateStopWord(StatesGroup):
    word = State()
    description = State()


class DeleteStopWord(StatesGroup):
    word = State()


def split_stop_words_by_pages(stop_words, page_size=30):
    """Разделяет стоп-слова на страницы для избежания MESSAGE_TOO_LONG"""
    pages = []
    for i in range(0, len(stop_words), page_size):
        pages.append(stop_words[i:i + page_size])
    return pages


@stop_words_router.callback_query(F.data == "stop_words")
async def stop_words_menu(callback_query: CallbackQuery):
    try:
        kb = InlineKeyboardBuilder()
        btn_list = InlineKeyboardButton(text="Список стоп-слов", callback_data="list_stop_words_0")
        btn_add = InlineKeyboardButton(text="Добавить стоп-слово", callback_data="add_stop_word")
        btn_delete = InlineKeyboardButton(text="Удалить стоп-слово", callback_data="delete_stop_word")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="back_to_main")
        
        kb.row(btn_list)
        kb.row(btn_add)
        kb.row(btn_delete)
        kb.row(btn_back)
        
        await callback_query.message.edit_text(
            "Управление стоп-словами:", reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@stop_words_router.callback_query(F.data.startswith("list_stop_words_"))
async def list_stop_words(callback_query: CallbackQuery):
    try:
        # Извлекаем номер страницы
        page = int(callback_query.data.split("_")[-1])
        
        stop_words = await repo.select_all()
        
        if not stop_words:
            kb = InlineKeyboardBuilder()
            btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
            kb.row(btn_back)
            await callback_query.message.edit_text(
                "Список стоп-слов пуст.", reply_markup=kb.as_markup()
            )
            return
        
        # Разделяем на страницы (максимум 30 слов на страницу)
        pages = split_stop_words_by_pages(stop_words, page_size=30)
        total_pages = len(pages)
        
        if page >= total_pages:
            page = 0
        
        current_page_words = pages[page]
        
        # Формируем текст для текущей страницы
        text = f"Список стоп-слов (страница {page + 1}/{total_pages}):\n\n"
        
        for i, sw in enumerate(current_page_words, start=page * 30 + 1):
            # Обрезаем очень длинные слова для отображения
            word_display = sw.word if len(sw.word) <= 50 else sw.word[:47] + "..."
            desc_display = ""
            if sw.description:
                desc_display = f" - {sw.description}" if len(sw.description) <= 30 else f" - {sw.description[:27]}..."
            
            text += f"{i}. {word_display}{desc_display}\n"
        
        text += f"\nВсего стоп-слов: {len(stop_words)}"
        
        # Создаем кнопки навигации
        kb = InlineKeyboardBuilder()
        
        # Кнопки навигации между страницами
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"list_stop_words_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"list_stop_words_{page + 1}"))
        
        if nav_buttons:
            if len(nav_buttons) == 2:
                kb.row(nav_buttons[0], nav_buttons[1])
            else:
                kb.row(nav_buttons[0])
        
        # Кнопка назад в меню
        btn_back = InlineKeyboardButton(text="Назад в меню", callback_data="stop_words")
        kb.row(btn_back)
        
        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
        
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@stop_words_router.callback_query(F.data == "add_stop_word")
async def add_stop_word(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.answer("Введите стоп-слово:")
        await state.set_state(CreateStopWord.word)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@stop_words_router.message(CreateStopWord.word)
async def add_stop_word_description(message: Message, state: FSMContext):
    try:
        await state.update_data(word=message.text.strip())
        await message.answer("Введите описание (или отправьте '-' чтобы пропустить):")
        await state.set_state(CreateStopWord.description)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@stop_words_router.message(CreateStopWord.description)
async def save_stop_word(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        word = data.get("word")
        description = message.text.strip() if message.text.strip() != "-" else ""
        
        await repo.add(word, description)
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
        kb.row(btn_back)
        
        await message.answer(
            f"Стоп-слово '{word}' успешно добавлено!", 
            reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@stop_words_router.callback_query(F.data == "delete_stop_word")
async def delete_stop_word(callback_query: CallbackQuery, state: FSMContext):
    try:
        await callback_query.message.answer("Введите стоп-слово для удаления (точно как оно записано):")
        await state.set_state(DeleteStopWord.word)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@stop_words_router.message(DeleteStopWord.word)
async def confirm_delete_stop_word(message: Message, state: FSMContext):
    try:
        word_to_delete = message.text.strip()
        
        # Попробуем найти точное совпадение
        all_stop_words = await repo.select_all()
        found_word = None
        
        for sw in all_stop_words:
            if sw.word == word_to_delete:
                found_word = sw.word
                break
        
        if found_word:
            await repo.delete_word(found_word)
            kb = InlineKeyboardBuilder()
            btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
            kb.row(btn_back)
            
            await message.answer(
                f"✅ Стоп-слово '{found_word}' успешно удалено!", 
                reply_markup=kb.as_markup()
            )
        else:
            # Если точного совпадения нет, покажем похожие варианты
            similar_words = []
            word_lower = word_to_delete.lower()
            
            for sw in all_stop_words:
                if (word_lower in sw.word.lower() or 
                    sw.word.lower() in word_lower or
                    # Проверяем без эмодзи
                    word_lower in sw.word.encode('ascii', 'ignore').decode().lower()):
                    similar_words.append(sw.word)
            
            if similar_words:
                similar_text = "\n".join([f"• {word}" for word in similar_words[:10]])
                await message.answer(
                    f"❌ Точное совпадение не найдено.\n\n"
                    f"Возможно, вы имели в виду:\n{similar_text}\n\n"
                    f"Скопируйте точное написание и попробуйте снова."
                )
            else:
                await message.answer(f"❌ Стоп-слово '{word_to_delete}' не найдено в базе данных.")
        
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
        await state.clear()