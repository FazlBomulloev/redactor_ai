import asyncio
import logging

from apscheduler.triggers.cron import CronTrigger

from aiogram import Dispatcher, Bot

from core.config import settings
from routers.admin import admin_router
from routers.command import command_router
from routers.events import event_router
from routers.publication import publication_router
from routers.publication_schedule import publication_schedule_router
from routers.statistics import statistics_router
from routers.thematic_blocks import thematic_blocks_router
from routers.stop_words import stop_words_router
from routers.ai_admin import ai_admin_router  # НОВЫЙ ИМПОРТ
from utils.shedule import scheduler, check_new_tasks, schedule_tasks
from utils.telethon import TelegramClientWrapper, telegram_client_wrapper
from utils.config_watcher import config_watcher
from utils.ai_manager import ai_manager  # НОВЫЙ ИМПОРТ

dp = Dispatcher()
bot = Bot(token="8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw")

api_id = 26515046
api_hash = "22b6dbdfce28e71ce66911f29ccc5bfe"

dp.include_router(command_router)
dp.include_router(thematic_blocks_router)
dp.include_router(publication_schedule_router)
dp.include_router(admin_router)
dp.include_router(event_router)
dp.include_router(statistics_router)
dp.include_router(publication_router)
dp.include_router(stop_words_router)
dp.include_router(ai_admin_router)

TelegramClient = telegram_client_wrapper


async def main():
    logging.basicConfig(level=logging.DEBUG)
    try:
        await TelegramClient.load_accounts()
        asyncio.create_task(TelegramClient.watch_for_new_accounts())
        asyncio.create_task(config_watcher.start_watching())
        
        logger = logging.getLogger(__name__)
        logger.info("Initializing AI Manager...")
        success = await ai_manager.initialize()
        if success:
            logger.info("AI Manager initialized successfully")
        else:
            logger.warning("AI Manager initialization failed, but continuing...")
        
        # Проверяем, не запущен ли уже планировщик
        if not scheduler.running:
            scheduler.start()
            print("Scheduler started")
        else:
            print("Scheduler already running")
            
        # Загружаем задачи
        await schedule_tasks()
        
        # Добавляем задачу проверки новых задач, если её ещё нет
        if not scheduler.get_job("check_new_tasks_job"):
            scheduler.add_job(check_new_tasks, CronTrigger(minute="*"), id="check_new_tasks_job")
            
        await dp.start_polling(bot)
    finally:
        print("Stop bot")
        await TelegramClient.disconnect_all()


async def restart_bot():
    """Перезапуск бота с новыми настройками"""
    print("Restarting bot with new settings...")
    
    # Останавливаем планировщик только если он запущен
    if scheduler.running:
        scheduler.shutdown(wait=False)
        await asyncio.sleep(1)  # Ждем завершения
    
    # Отключаем Telegram клиенты
    await TelegramClient.disconnect_all()
    
    # Перезагружаем настройки
    from core.config import reload_settings
    reload_settings()
    
    # Перезапускаем все компоненты
    await TelegramClient.load_accounts()
    asyncio.create_task(TelegramClient.watch_for_new_accounts())
    
    # Перезагружаем AI Manager
    await ai_manager.reload_configuration()
    
    # Создаем новый планировщик если нужно
    if not scheduler.running:
        scheduler.start()
        
    await schedule_tasks()
    
    # Добавляем задачу проверки, если её нет
    if not scheduler.get_job("check_new_tasks_job"):
        scheduler.add_job(check_new_tasks, CronTrigger(minute="*"), id="check_new_tasks_job")
    
    print("Bot restarted successfully")


if __name__ == "__main__":
    asyncio.run(main())