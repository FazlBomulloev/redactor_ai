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


@stop_words_router.callback_query(F.data == "stop_words")
async def stop_words_menu(callback_query: CallbackQuery):
    try:
        kb = InlineKeyboardBuilder()
        btn_list = InlineKeyboardButton(text="Список стоп-слов", callback_data="list_stop_words")
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


@stop_words_router.callback_query(F.data == "list_stop_words")
async def list_stop_words(callback_query: CallbackQuery):
    try:
        stop_words = await repo.select_all()
        
        if not stop_words:
            kb = InlineKeyboardBuilder()
            btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
            kb.row(btn_back)
            await callback_query.message.edit_text(
                "Список стоп-слов пуст.", reply_markup=kb.as_markup()
            )
            return
        
        text = "Список стоп-слов:\n\n"
        for i, sw in enumerate(stop_words, 1):
            text += f"{i}. {sw.word}"
            if sw.description:
                text += f" - {sw.description}"
            text += "\n"
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
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
        await callback_query.message.answer("Введите стоп-слово для удаления:")
        await state.set_state(DeleteStopWord.word)
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@stop_words_router.message(DeleteStopWord.word)
async def confirm_delete_stop_word(message: Message, state: FSMContext):
    try:
        word = message.text.strip()
        await repo.delete_word(word)
        
        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="stop_words")
        kb.row(btn_back)
        
        await message.answer(
            f"Стоп-слово '{word}' успешно удалено!", 
            reply_markup=kb.as_markup()
        )
        await state.clear()
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
