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
from routers.ai_admin import ai_admin_router
from utils.shedule import scheduler, check_new_tasks, schedule_tasks
from utils.telethon import TelegramClientWrapper, telegram_client_wrapper
from utils.config_watcher import config_watcher
from utils.ai_manager import ai_manager
from utils.text_corrector import integrate_corrector

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
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Integrating text corrector...")
        if integrate_corrector():
            logger.info("✅ Text corrector integrated successfully")
        else:
            logger.warning("⚠️ Text corrector integration failed, but continuing...")
        
        await TelegramClient.load_accounts()
        asyncio.create_task(TelegramClient.watch_for_new_accounts())
        asyncio.create_task(config_watcher.start_watching())
        
        logger.info("Initializing AI Manager...")
        success = await ai_manager.initialize()
        if success:
            logger.info("✅ AI Manager initialized successfully")
        else:
            logger.warning("⚠️ AI Manager initialization failed, but continuing...")
        
        # Проверяем, не запущен ли уже планировщик
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Scheduler started")
        else:
            logger.info("⚠️ Scheduler already running")
            
        # Загружаем задачи
        await schedule_tasks()
        
        # Добавляем задачу проверки новых задач, если её ещё нет
        if not scheduler.get_job("check_new_tasks_job"):
            scheduler.add_job(check_new_tasks, CronTrigger(minute="*"), id="check_new_tasks_job")
            
        logger.info("🚀 Starting bot polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Error during startup: {e}")
        raise
    finally:
        logger.info("🛑 Stopping bot...")
        await TelegramClient.disconnect_all()


async def restart_bot():
    """Перезапуск бота с новыми настройками"""
    logger = logging.getLogger(__name__)
    logger.info("🔄 Restarting bot with new settings...")
    
    try:
        # Останавливаем планировщик только если он запущен
        if scheduler.running:
            scheduler.shutdown(wait=False)
            await asyncio.sleep(1)  # Ждем завершения
            logger.info("⏹️ Scheduler stopped")
        
        # Отключаем Telegram клиенты
        await TelegramClient.disconnect_all()
        logger.info("📱 Telegram clients disconnected")
        
        # Перезагружаем настройки
        from core.config import reload_settings
        reload_settings()
        logger.info("⚙️ Settings reloaded")
        
        
        if integrate_corrector():
            logger.info("✅ Text corrector re-integrated")
        
        # Перезапускаем все компоненты
        await TelegramClient.load_accounts()
        asyncio.create_task(TelegramClient.watch_for_new_accounts())
        
        # Перезагружаем AI Manager
        await ai_manager.reload_configuration()
        logger.info("🤖 AI Manager reloaded")
        
        # Создаем новый планировщик если нужно
        if not scheduler.running:
            scheduler.start()
            logger.info("✅ Scheduler restarted")
            
        await schedule_tasks()
        
        # Добавляем задачу проверки, если её нет
        if not scheduler.get_job("check_new_tasks_job"):
            scheduler.add_job(check_new_tasks, CronTrigger(minute="*"), id="check_new_tasks_job")
        
        logger.info("✅ Bot restarted successfully")
        
    except Exception as e:
        logger.error(f"❌ Error during restart: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())