# routers/statistics_router.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from core.repositories.article import ArticleRepository
from utils.telethon import telegram_client_wrapper

statistics_router = Router()


@statistics_router.callback_query(F.data == "statistics")
async def show_statistics(callback_query: CallbackQuery):
    try:
        # Создаем экземпляр репозитория (предполагается, что session уже настроен)
        repo_pb = ArticleRepository()

        stats = await repo_pb.get_statistics()
        stats_text = (
            f"Количество знаков за вчера: {stats['yesterday_chars']}\n"
            f"Количество знаков за 30 дней: {stats['last_30_days_chars']}\n"
            f"Среднее количество знаков в день: {stats['avg_chars_per_day']}\n"
            f"Среднее количество знаков в публикации: {stats['avg_chars_per_publication']}\n"
            f"Количество публикаций за вчера: {stats['yesterday_publications']}\n"
            f"Количество публикаций за 30 дней: {stats['last_30_days_publications']}\n"
        )

        kb = InlineKeyboardBuilder()
        kb.add(InlineKeyboardButton(text="Назад", callback_data="back_to_main"))

        await callback_query.message.edit_text(stats_text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@statistics_router.callback_query(F.data == "statistics")
async def statistics_menu(callback_query: CallbackQuery):
    try:
        kb = InlineKeyboardBuilder()
        btn_accounts = InlineKeyboardButton(text="Статистика аккаунтов", callback_data="accounts_stats")
        btn_publications = InlineKeyboardButton(text="Статистика публикаций", callback_data="publications_stats")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="main_menu")

        kb.row(btn_accounts)
        kb.row(btn_publications)
        kb.row(btn_back)

        await callback_query.message.edit_text(
            "Статистика:", reply_markup=kb.as_markup()
        )
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@statistics_router.callback_query(F.data == "accounts_stats")
async def accounts_statistics(callback_query: CallbackQuery):
    try:
        total_accounts = len(telegram_client_wrapper._clients)
        current_account = telegram_client_wrapper.current_client_key

        text = f"📊 Статистика аккаунтов:\n\n"
        text += f"Всего активных аккаунтов: {total_accounts}\n"

        if current_account:
            text += f"Текущий аккаунт: {current_account}\n\n"
            text += "Список активных аккаунтов:\n"
            for i, account in enumerate(telegram_client_wrapper._clients.keys(), 1):
                status = "🟢 (активный)" if account == current_account else "⚪"
                text += f"{i}. {account} {status}\n"
        else:
            text += "❌ Нет активных аккаунтов\n"

        kb = InlineKeyboardBuilder()
        btn_refresh = InlineKeyboardButton(text="🔄 Обновить", callback_data="accounts_stats")
        btn_back = InlineKeyboardButton(text="Назад", callback_data="statistics")
        kb.row(btn_refresh)
        kb.row(btn_back)

        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")


@statistics_router.callback_query(F.data == "publications_stats")
async def publications_statistics(callback_query: CallbackQuery):
    try:
        # Здесь можно добавить статистику публикаций
        text = "📈 Статистика публикаций:\n\n"
        text += "Функция в разработке..."

        kb = InlineKeyboardBuilder()
        btn_back = InlineKeyboardButton(text="Назад", callback_data="statistics")
        kb.row(btn_back)

        await callback_query.message.edit_text(text, reply_markup=kb.as_markup())
    except Exception as e:
        await callback_query.message.answer(f"Ошибка: {e}")
