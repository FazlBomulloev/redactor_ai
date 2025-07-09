import logging
import asyncio
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
import os

# Настройки для логов медиа
LOG_CHAT_ID = -1002597796340  # Чат для логов медиа
ADMIN_BOT_TOKEN = "8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw"

class MediaTelegramHandler(logging.Handler):
    def __init__(self, bot_token, chat_id):
        super().__init__()
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id
        self.last_send_time = {}
        self.min_interval = 2  # Минимальный интервал между сообщениями
        
    async def safe_send_log(self, message, max_retries=2):
        """Безопасная отправка логов медиа"""
        for attempt in range(max_retries):
            try:
                if len(message) > 4000:
                    message = message[:3900] + "...[cut]"
                    
                await self.bot.send_message(self.chat_id, message)
                return True
            except TelegramRetryAfter as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(e.retry_after)
                else:
                    return False
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                else:
                    return False
        return False

    def emit(self, record):
        """Отправка лога медиа в Telegram"""
        try:
            # Проверяем интервал между отправками
            current_time = datetime.now().timestamp()
            if record.levelno in self.last_send_time:
                if current_time - self.last_send_time[record.levelno] < self.min_interval:
                    return
            
            self.last_send_time[record.levelno] = current_time
            
            # Форматируем сообщение
            level_emoji = {
                logging.INFO: "📸",
                logging.WARNING: "⚠️", 
                logging.ERROR: "❌"
            }
            
            emoji = level_emoji.get(record.levelno, "📝")
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"{emoji} {timestamp} | {record.getMessage()}"
            
            # Отправляем асинхронно
            asyncio.create_task(self.safe_send_log(message))
            
        except Exception:
            pass  # Игнорируем ошибки в логировании

# Настройка логгера для медиа
def setup_media_logging():
    """Настройка логирования только для медиа"""
    
    # Создаем директорию для логов
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Логгер для медиа
    media_logger = logging.getLogger("media")
    media_logger.setLevel(logging.INFO)
    media_logger.handlers.clear()
    
    # Хэндлер для файла (только медиа логи)
    file_handler = logging.FileHandler(
        f"{log_dir}/media_{datetime.now().strftime('%Y%m%d')}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Хэндлер для Telegram (только медиа)
    telegram_handler = MediaTelegramHandler(ADMIN_BOT_TOKEN, LOG_CHAT_ID)
    telegram_handler.setLevel(logging.INFO)
    
    # Добавляем хэндлеры
    media_logger.addHandler(file_handler)
    media_logger.addHandler(telegram_handler)
    
    return media_logger

# Создаем медиа логгер
media_logger = setup_media_logging()

# Функции для логирования медиа
async def log_media_start(message_id, has_media, text_length):
    """Начало обработки сообщения"""
    media_status = "📸 WITH MEDIA" if has_media else "📝 TEXT ONLY"
    media_logger.info(f"Processing msg {message_id} | {media_status} | Text: {text_length} chars")

async def log_media_group_found(message_id, group_id, count):
    """Найдена медиа группа"""
    media_logger.info(f"Media group | Msg: {message_id} | Group: {group_id} | Count: {count}")

async def log_media_processing(message_id, total_count, media_types):
    """Обработка медиа файлов"""
    media_logger.info(f"Processing media | Msg: {message_id} | Total: {total_count} | Types: {media_types}")

async def log_media_download(message_id, media_num, media_type, size_mb=None):
    """Скачивание медиа"""
    size_info = f" ({size_mb:.1f}MB)" if size_mb else ""
    media_logger.info(f"Download {media_type} {media_num} | Msg: {message_id}{size_info}")

async def log_media_skip(message_id, media_num, reason):
    """Пропуск медиа"""
    media_logger.warning(f"Skip media {media_num} | Msg: {message_id} | Reason: {reason}")

async def log_media_final(message_id, final_count, text_length):
    """Финальный результат обработки"""
    media_logger.info(f"Final result | Msg: {message_id} | Media: {final_count} | Text: {text_length} chars")

async def log_send_start(channel, text_length, media_count):
    """Начало отправки в канал"""
    media_logger.info(f"Sending to {channel} | Text: {text_length} chars | Media: {media_count} files")

async def log_send_method(method, count=None):
    """Метод отправки"""
    if method == "single_photo":
        media_logger.info("📸 Sending single photo with caption")
    elif method == "single_video":
        media_logger.info("🎥 Sending single video with caption")
    elif method == "media_group":
        media_logger.info(f"📸🎥 Sending media group with {count} items")
    elif method == "text_only":
        media_logger.info("📝 Sending text-only message")
    elif method == "fallback_text":
        media_logger.warning("📝 Fallback: sending text after media error")

async def log_send_success(media_count=0):
    """Успешная отправка"""
    if media_count > 0:
        media_logger.info(f"✅ Media sent successfully | Count: {media_count}")
    else:
        media_logger.info("✅ Text sent successfully")

async def log_send_error(error_msg, media_count=0):
    """Ошибка отправки"""
    context = f"with {media_count} media" if media_count > 0 else "text-only"
    media_logger.error(f"❌ Send failed ({context}): {error_msg[:200]}")

async def log_media_error(message_id, error_msg):
    """Общая ошибка обработки медиа"""
    media_logger.error(f"❌ Media error | Msg: {message_id} | Error: {error_msg[:200]}")

# Функция для быстрого логирования
def get_media_logger():
    """Получить медиа логгер"""
    return media_logger