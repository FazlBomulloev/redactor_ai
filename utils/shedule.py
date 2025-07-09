import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core.config import settings, reload_settings
from core.repositories.event import EventRepository
from core.repositories.publication_schedule import PublicationScheduleRepository
from core.repositories.publication import PublicationRepository
from .telegram import main as main_pub
from .events import main as main_ev

bot = Bot(token="7256604422:AAFFAxojKkoFYT5zBbyGJ1ThbUyv-sQJEwo")


async def sh_ind_pub(pb):
    if pb.media:
        if pb.media.startswith(
                "AgAC"
        ):  # Предположим, что file_id фото начинается с "AgAC"
            await bot.send_photo(
                settings.channel__link,
                pb.media,
                caption=pb.text,
            )
        elif pb.media.startswith(
                "BAAC"
        ):  # Предположим, что file_id видео начинается с "BAAC"
            await bot.send_video(
                settings.channel__link,
                pb.media,
                caption=pb.text,
            )
        else:
            await bot.send_message(settings.channel__link, pb.text)
    else:
        await bot.send_message(settings.channel__link, pb.text)


repo = PublicationScheduleRepository()
repo_pb = PublicationRepository()
repo_ev = EventRepository()
scheduler = AsyncIOScheduler()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def schedule_tasks():
    # Удаляем все существующие задачи перед пересозданием
    for job in scheduler.get_jobs():
        if job.id.startswith("task_") or job.id.startswith("event_"):
            scheduler.remove_job(job.id)

    tasks = await repo.select_all()
    for task in tasks:
        hour, minute = map(int, task.time.split(":"))
        # Определение дней недели в зависимости от параметра task.today
        if task.today == 0:
            trigger = CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri")
        elif task.today == 5:
            trigger = CronTrigger(hour=hour, minute=minute, day_of_week="sat,sun")
        else:
            logger.warning(f"Unknown task.today value: {task.today} for task {task.id}")
            continue

        job_id = f"task_{task.id}"

        # Проверяем есть ли тематические блоки или индивидуальная публикация
        if task.thematic_block_id and str(task.thematic_block_id).strip() and str(task.thematic_block_id) != "0":
            task_id = str(task.thematic_block_id).split(",")
            scheduler.add_job(main_pub, trigger=trigger, id=job_id, args=[task_id])
        elif task.ind_pub_id and task.ind_pub_id != 0:
            publ = await repo_pb.select_id(task.ind_pub_id)
            scheduler.add_job(sh_ind_pub, trigger=trigger, id=job_id, args=[publ])
        # Если нет ни тематических блоков, ни индивидуальной публикации - не создаем задачу

    events = await repo_ev.select_all()
    for event in events:
        start_hour, start_minute = map(int, event.time_in.split(":"))
        end_hour, end_minute = map(int, event.time_out.split(":"))
        interval_minutes = int(event.interval)

        # Создание триггеров для каждого промежутка времени
        current_time = datetime.now()
        start_time = current_time.replace(
            hour=start_hour, minute=start_minute, second=0, microsecond=0
        )
        end_time = current_time.replace(
            hour=end_hour, minute=end_minute, second=0, microsecond=0
        )

        if start_time > end_time:
            end_time += timedelta(days=1)

        while start_time < end_time:
            trigger = CronTrigger(hour=start_time.hour, minute=start_time.minute)
            job_id = f"event_{event.id}_{start_time.strftime('%H%M')}"
            if not scheduler.get_job(job_id):
                scheduler.add_job(main_ev, trigger=trigger, id=job_id, args=[event.id])
            start_time += timedelta(minutes=interval_minutes)


async def update_scheduler():
    """Полное обновление планировщика"""
    logger.info("Updating scheduler...")
    await schedule_tasks()


async def check_new_tasks():
    logger.info("Checking for new tasks...")
    await update_scheduler()


async def restart_scheduler():
    """Перезапуск планировщика с обновленными настройками"""
    global scheduler
    
    logger.info("Restarting scheduler with updated settings...")

    # Проверяем, запущен ли планировщик, и останавливаем его
    if scheduler.running:
        logger.info("Stopping running scheduler...")
        scheduler.shutdown(wait=False)
        # Ждем немного для корректного завершения
        await asyncio.sleep(1)

    # Перезагружаем настройки
    reload_settings()

    # Создаем новый планировщик, если нужно
    if not scheduler.running:
        scheduler = AsyncIOScheduler()

    # Запускаем планировщик заново
    scheduler.start()
    logger.info("Scheduler started")

    # Пересоздаем все задачи с новыми настройками
    await schedule_tasks()

    # Добавляем задачу проверки новых задач
    if not scheduler.get_job("check_new_tasks_job"):
        scheduler.add_job(check_new_tasks, CronTrigger(minute="*"), id="check_new_tasks_job")

    logger.info("Scheduler restarted successfully with new settings")


async def update_channel_settings():
    """Обновляет настройки канала без перезапуска планировщика"""
    reload_settings()
    # Обновляем target_chat_id в telegram.py
    from utils.telegram import update_target_chat_id
    await update_target_chat_id()
    logger.info("Channel settings updated successfully")