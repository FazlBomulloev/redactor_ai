import asyncio
import logging
import time
from typing import List, Tuple, Optional
from mistralai import Mistral

# Настройки корректора
CORRECTOR_API_KEY = "FVved5ohmgoHYYFh7uK2laq5rQNAzgZ5"
AGENT_750_ID = "ag:9885ec37:20250704:korrektor-750-znakov:c3b0c672"
AGENT_3500_ID = "ag:9885ec37:20250704:korrektor-3500-znakov:73df2f34"

# Константы для правил
MEDIA_MIN_THRESHOLD = 750
MEDIA_MAX_THRESHOLD = 1200
TEXT_MAX_THRESHOLD = 3500
FIRST_PART_LENGTH = 700
CONTINUATION_MAX_LENGTH = 3500

# Эмодзи для разделения частей
CONTINUATION_DOWN = " 👇👇👇"
CONTINUATION_UP = "👆👆👆 "

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента AI
corrector_client = Mistral(api_key=CORRECTOR_API_KEY)

# Контроль частоты запросов
MISTRAL_REQUEST_DELAY = 0.3
last_corrector_request_time = 0


class TextCorrectorResult:
    """Результат обработки текста корректором"""
    def __init__(self, parts: List[str], needs_split: bool = False, was_corrected: bool = False):
        self.parts = parts
        self.needs_split = needs_split
        self.was_corrected = was_corrected
        
    @property
    def first_part(self) -> str:
        return self.parts[0] if self.parts else ""
    
    @property
    def continuation_parts(self) -> List[str]:
        return self.parts[1:] if len(self.parts) > 1 else []


class TextCorrector:
    """Корректор текста согласно техническому заданию"""
    
    def __init__(self):
        self.client = corrector_client
        
    async def correct_text_750(self, text: str, retries: int = 3) -> Optional[str]:
        """Коррекция текста до 750 символов через AI агента"""
        global last_corrector_request_time
        
        logger.info(f"Correcting text to 750 chars, length: {len(text)}")
        
        # Контроль частоты запросов
        current_time = time.time()
        time_since_last = current_time - last_corrector_request_time
        if time_since_last < MISTRAL_REQUEST_DELAY:
            wait_time = MISTRAL_REQUEST_DELAY - time_since_last
            await asyncio.sleep(wait_time)
        
        for attempt in range(retries):
            try:
                logger.info(f"Sending correction request to 750-char agent (attempt {attempt + 1})")
                
                response = await self.client.agents.complete_async(
                    agent_id=AGENT_750_ID,
                    messages=[{"role": "user", "content": text}]
                )
                
                last_corrector_request_time = time.time()
                corrected_text = response.choices[0].message.content.strip()
                
                logger.info(f"AI corrected text: {len(corrected_text)} chars")
                return corrected_text
                
            except Exception as e:
                logger.error(f"Error correcting text to 750 chars (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                
        logger.error("Failed to correct text to 750 chars after all retries")
        return None
    
    async def correct_text_3500(self, text: str, retries: int = 3) -> Optional[str]:
        """Коррекция текста до 3500 символов через AI агента"""
        global last_corrector_request_time
        
        logger.info(f"Correcting text to 3500 chars, length: {len(text)}")
        
        # Контроль частоты запросов
        current_time = time.time()
        time_since_last = current_time - last_corrector_request_time
        if time_since_last < MISTRAL_REQUEST_DELAY:
            wait_time = MISTRAL_REQUEST_DELAY - time_since_last
            await asyncio.sleep(wait_time)
        
        for attempt in range(retries):
            try:
                logger.info(f"Sending correction request to 3500-char agent (attempt {attempt + 1})")
                
                response = await self.client.agents.complete_async(
                    agent_id=AGENT_3500_ID,
                    messages=[{"role": "user", "content": text}]
                )
                
                last_corrector_request_time = time.time()
                corrected_text = response.choices[0].message.content.strip()
                
                logger.info(f"AI corrected text: {len(corrected_text)} chars")
                return corrected_text
                
            except Exception as e:
                logger.error(f"Error correcting text to 3500 chars (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                
        logger.error("Failed to correct text to 3500 chars after all retries")
        return None
    
    def split_text_by_chunks(self, text: str, max_length: int) -> List[str]:
        """Разбивает текст на части по указанной длине, учитывая знаки препинания"""
        if len(text) <= max_length:
            return [text]
        
        parts = []
        remaining_text = text
        
        while len(remaining_text) > max_length:
            split_pos = max_length
            
            # Ищем лучшее место для разрыва в порядке приоритета:
            # 1. Точка + пробел (конец предложения)
            # 2. Восклицательный/вопросительный знак + пробел  
            
            # Ищем конец предложения (точка + пробел)
            for i in range(max_length - 1, max_length * 0.7, -1):
                if i < len(remaining_text) - 1:
                    if remaining_text[i] == '.' and remaining_text[i + 1] == ' ':
                        split_pos = i + 1  # Включаем точку, исключаем пробел
                        break
                    elif remaining_text[i] in '!?' and remaining_text[i + 1] == ' ':
                        split_pos = i + 1  # Включаем знак, исключаем пробел
                        break
            
            
            part = remaining_text[:split_pos].rstrip()
            parts.append(part)
            remaining_text = remaining_text[split_pos:].lstrip()
        
        if remaining_text:
            parts.append(remaining_text)
        
        return parts
    
    async def process_text_with_media(self, text: str) -> TextCorrectorResult:
        """Обработка текста с медиа согласно правилам"""
        text_length = len(text)
        logger.info(f"Processing text with media: {text_length} chars")
        
        if text_length <= MEDIA_MIN_THRESHOLD:
            # Текст короткий, возвращаем как есть
            logger.info("Text is short enough, no correction needed")
            return TextCorrectorResult([text])
        
        elif MEDIA_MIN_THRESHOLD < text_length <= MEDIA_MAX_THRESHOLD:
            # Правило: "медиа + (750 - 1200)" - коррекция через AI
            logger.info("Text needs correction to 750 chars")
            corrected = await self.correct_text_750(text)
            
            if corrected:
                return TextCorrectorResult([corrected], was_corrected=True)
            else:
                # Если AI не сработал, возвращаем оригинал
                logger.warning("AI correction failed, returning original")
                return TextCorrectorResult([text])
        
        else:
            # Правило: "медиа + (1200 +)" - разделение на части
            logger.info("Text needs splitting into multiple parts")
            
            # Первая часть: 700 символов + эмодзи
            first_part = text[:FIRST_PART_LENGTH].rstrip()
            # Ищем последний пробел для красивого разрыва
            last_space = first_part.rfind(' ')
            if last_space > FIRST_PART_LENGTH * 0.8:
                first_part = first_part[:last_space]
            
            first_part += CONTINUATION_DOWN
            
            # Остальной текст
            remaining_text = text[len(first_part) - len(CONTINUATION_DOWN):].lstrip()
            
            # Разбиваем остальной текст на части по 3500 символов
            continuation_parts = self.split_text_by_chunks(remaining_text, CONTINUATION_MAX_LENGTH)
            
            # Добавляем эмодзи к частям
            processed_parts = [first_part]
            
            for i, part in enumerate(continuation_parts):
                if i == len(continuation_parts) - 1:
                    # Последняя часть - без эмодзи в конце
                    processed_part = CONTINUATION_UP + part
                else:
                    # Промежуточная часть - с эмодзи в начале и конце
                    processed_part = CONTINUATION_UP + part + CONTINUATION_DOWN
                
                processed_parts.append(processed_part)
            
            logger.info(f"Split into {len(processed_parts)} parts")
            return TextCorrectorResult(processed_parts, needs_split=True)
    
    async def process_text_without_media(self, text: str) -> TextCorrectorResult:
        """Обработка текста без медиа согласно правилу "3500+" """
        text_length = len(text)
        logger.info(f"Processing text without media: {text_length} chars")
        
        if text_length <= TEXT_MAX_THRESHOLD:
            # Текст короткий, возвращаем как есть
            logger.info("Text is short enough, no correction needed")
            return TextCorrectorResult([text])
        else:
            # Правило: "3500+" - коррекция через AI
            logger.info("Text needs correction to 3500 chars")
            corrected = await self.correct_text_3500(text)
            
            if corrected:
                return TextCorrectorResult([corrected], was_corrected=True)
            else:
                # Если AI не сработал, возвращаем оригинал
                logger.warning("AI correction failed, returning original")
                return TextCorrectorResult([text])
    
    async def process_message(self, text: str, has_media: bool = False) -> TextCorrectorResult:
        """Главная функция обработки сообщения"""
        logger.info(f"Processing message: {len(text)} chars, has_media: {has_media}")
        
        if not text or not text.strip():
            logger.warning("Empty text provided")
            return TextCorrectorResult([])
        
        text = text.strip()
        
        if has_media:
            return await self.process_text_with_media(text)
        else:
            return await self.process_text_without_media(text)


async def send_continuation_parts_after_bot_reply(continuation_parts, channel_username, bot_token, first_part_message_id, max_wait_time=120):
    """
    Отправляет продолжения после получения ответа бота с ID на первую часть
    Ждет ответ бота вида "Редакторский канал ... id: 12345" на конкретное сообщение
    
    Args:
        continuation_parts: Список частей для отправки
        channel_username: Имя канала
        bot_token: Токен бота
        first_part_message_id: ID первой части (полученный при отправке)
        max_wait_time: Максимальное время ожидания в секундах
    """
    from utils.telethon import telegram_client_wrapper
    
    logger.info(f"Waiting for bot reply on message ID {first_part_message_id} before sending {len(continuation_parts)} parts")
    
    try:
        client = await telegram_client_wrapper.get_current_client_safe()
        channel = await client.get_entity(channel_username)
        
        # Ждем ответа бота с ID на конкретное сообщение
        start_time = asyncio.get_event_loop().time()
        bot_reply_found = False
        
        while not bot_reply_found and (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            await asyncio.sleep(3)  # Проверяем каждые 3 секунды
            
            try:
                # Получаем последние сообщения
                recent_messages = await client.get_messages(channel, limit=20)
                
                # Ищем ответ бота именно на наше сообщение
                for message in recent_messages:
                    # Проверяем, есть ли ответ бота с ID на НАШУ первую часть
                    if (message.reply_to and 
                        message.reply_to.reply_to_msg_id == first_part_message_id and
                        message.text and "id:" in message.text.lower()):
                        
                        bot_reply_found = True
                        extracted_id = message.text.split("id:")[-1].strip()
                        logger.info(f"Bot reply found for message {first_part_message_id}! Extracted ID: {extracted_id}")
                        break
                    
            except Exception as e:
                logger.warning(f"Error checking for bot reply: {e}")
                await asyncio.sleep(5)  # Увеличиваем интервал при ошибке
        
        if not bot_reply_found:
            logger.warning(f"No bot reply found for message {first_part_message_id} after {max_wait_time}s, sending continuations anyway")
        
        # Небольшая дополнительная пауза
        await asyncio.sleep(2)
        
        # Отправляем продолжения
        from aiogram import Bot
        async with Bot(token=bot_token) as bot:
            for i, part in enumerate(continuation_parts):
                try:
                    logger.info(f"Sending continuation part {i + 1}/{len(continuation_parts)}: {len(part)} chars")
                    await bot.send_message(chat_id=channel_username, text=part)
                    
                    # Пауза между частями
                    if i < len(continuation_parts) - 1:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error sending continuation part {i + 1}: {e}")
                    # Продолжаем отправку остальных частей
        
        logger.info("All continuation parts sent successfully")
        
    except Exception as e:
        logger.error(f"Error in send_continuation_parts_after_media: {e}")
        # В случае ошибки отправляем продолжения с фиксированной задержкой
        await asyncio.sleep(10)
        
        try:
            from aiogram import Bot
            async with Bot(token=bot_token) as bot:
                for i, part in enumerate(continuation_parts):
                    logger.info(f"Fallback sending part {i + 1}: {len(part)} chars")
                    await bot.send_message(chat_id=channel_username, text=part)
                    if i < len(continuation_parts) - 1:
                        await asyncio.sleep(1)
        except Exception as e2:
            logger.error(f"Fallback sending also failed: {e2}")


# Глобальный экземпляр корректора
text_corrector = TextCorrector()


def should_use_corrector(text: str, has_media: bool = False) -> bool:
    """Проверяет, нужно ли использовать корректор для данного текста"""
    if not text:
        return False
    
    text_length = len(text.strip())
    
    if has_media:
        return text_length > MEDIA_MIN_THRESHOLD
    else:
        return text_length > TEXT_MAX_THRESHOLD


async def enhanced_send_to_channel(text, media_list, channel_username, telethon_client, bot_token="8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw"):
    import tempfile, shutil
    from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
    from aiogram import Bot
    from aiogram.types import FSInputFile, InputMediaPhoto, InputMediaVideo

    temp_dir = tempfile.mkdtemp(prefix="telethon_media_")
    media_paths = []
    
    text_length = len(text) if text else 0
    media_count = len(media_list) if media_list else 0
    
    # Логирование из существующей системы
    from logger import log_send_start, log_send_method, log_send_success, log_send_error, log_media_error
    await log_send_start(channel_username, text_length, media_count)

    try:
        # Проверяем, нужна ли коррекция текста
        if text and should_use_corrector(text, bool(media_list)):
            logger.info(f"Text needs correction: {len(text)} chars, has_media: {bool(media_list)}")
            
            # Обрабатываем через корректор
            correction_result = await text_corrector.process_message(text, bool(media_list))
            
            if not correction_result.parts:
                logger.error("Corrector returned empty result")
                return False
            
            # Отправляем первую часть с медиа
            first_part = correction_result.first_part
            logger.info(f"Sending corrected first part: {len(first_part)} chars")
            
            sent_message = None
            
            # Скачиваем медиа если есть
            if media_list:
                for i, media in enumerate(media_list):
                    try:
                        if isinstance(media, MessageMediaDocument):
                            doc = media.document
                            if doc.mime_type:
                                if doc.mime_type.startswith("video/") or doc.mime_type.startswith("image/"):
                                    path = await telethon_client.download_media(media, file=temp_dir)
                                    if path:
                                        media_type = "video" if doc.mime_type.startswith("video/") else "photo"
                                        media_paths.append((path, media_type))
                        elif isinstance(media, MessageMediaPhoto):
                            path = await telethon_client.download_media(media, file=temp_dir)
                            if path:
                                media_paths.append((path, "photo"))
                    except Exception as e:
                        await log_media_error("download", f"Error downloading media {i + 1}: {e}")
                        continue

            # Отправляем первую часть и ПОЛУЧАЕМ ID отправленного сообщения
            async with Bot(token=bot_token) as bot:
                if media_paths:
                    if len(media_paths) == 1:
                        path, media_type = media_paths[0]
                        input_file = FSInputFile(path)
                        if media_type == "photo":
                            await log_send_method("single_photo")
                            sent_message = await bot.send_photo(chat_id=channel_username, photo=input_file, caption=first_part)
                        else:
                            await log_send_method("single_video")
                            sent_message = await bot.send_video(chat_id=channel_username, video=input_file, caption=first_part)
                    else:
                        # Отправляем как альбом
                        await log_send_method("media_group", len(media_paths))
                        media_group = []
                        for i, (path, media_type) in enumerate(media_paths[:3]):
                            input_file = FSInputFile(path)
                            caption = first_part if i == 0 and first_part else None
                            if media_type == "photo":
                                media = InputMediaPhoto(media=input_file, caption=caption)
                            else:
                                media = InputMediaVideo(media=input_file, caption=caption)
                            media_group.append(media)

                        sent_messages = await bot.send_media_group(chat_id=channel_username, media=media_group)
                        sent_message = sent_messages[0] if sent_messages else None
                elif first_part:
                    await log_send_method("text_only")
                    sent_message = await bot.send_message(chat_id=channel_username, text=first_part)

            # Отправляем продолжения если есть И если получили ID первой части
            if correction_result.continuation_parts and sent_message:
                logger.info(f"Scheduling {len(correction_result.continuation_parts)} continuation parts for message ID: {sent_message.message_id}")
                
                # Запускаем отправку продолжений в фоновом режиме с конкретным ID
                asyncio.create_task(
                    send_continuation_parts_after_bot_reply(
                        correction_result.continuation_parts,
                        channel_username,
                        bot_token,
                        sent_message.message_id  # Передаем конкретный ID первой части
                    )
                )

            await log_send_success(len(media_paths))
            return True
            
        else:
            # Используем оригинальную логику отправки
            logger.info("Text doesn't need correction, using original logic")
            
            # Скачиваем все файлы
            if media_list:
                for i, media in enumerate(media_list):
                    try:
                        if isinstance(media, MessageMediaDocument):
                            doc = media.document
                            if doc.mime_type:
                                if doc.mime_type.startswith("video/") or doc.mime_type.startswith("image/"):
                                    path = await telethon_client.download_media(media, file=temp_dir)
                                    if path:
                                        media_type = "video" if doc.mime_type.startswith("video/") else "photo"
                                        media_paths.append((path, media_type))
                        elif isinstance(media, MessageMediaPhoto):
                            path = await telethon_client.download_media(media, file=temp_dir)
                            if path:
                                media_paths.append((path, "photo"))
                    except Exception as e:
                        await log_media_error("download", f"Error downloading media {i + 1}: {e}")
                        continue

            async with Bot(token=bot_token) as bot:
                if media_paths:
                    if len(media_paths) == 1:
                        path, media_type = media_paths[0]
                        input_file = FSInputFile(path)
                        if media_type == "photo":
                            await log_send_method("single_photo")
                            await bot.send_photo(chat_id=channel_username, photo=input_file, caption=text)
                        else:
                            await log_send_method("single_video")
                            await bot.send_video(chat_id=channel_username, video=input_file, caption=text)
                    else:
                        # Отправляем как альбом
                        await log_send_method("media_group", len(media_paths))
                        media_group = []
                        for i, (path, media_type) in enumerate(media_paths[:3]):
                            input_file = FSInputFile(path)
                            caption = text if i == 0 and text else None
                            if media_type == "photo":
                                media = InputMediaPhoto(media=input_file, caption=caption)
                            else:
                                media = InputMediaVideo(media=input_file, caption=caption)
                            media_group.append(media)

                        await bot.send_media_group(chat_id=channel_username, media=media_group)

                    await log_send_success(len(media_paths))
                    return True

                elif text:
                    await log_send_method("text_only")
                    await bot.send_message(chat_id=channel_username, text=text)
                    await log_send_success(0)
                    return True

            return False

    except Exception as e:
        await log_send_error(str(e), media_count)
        
        # Если не удалось отправить с медиа, попробуем отправить только текст
        if text:
            try:
                async with Bot(token=bot_token) as bot:
                    await log_send_method("fallback_text")
                    await bot.send_message(chat_id=channel_username, text=text)
                    await log_send_success(0)
                    return True
            except Exception as e2:
                await log_send_error(f"Fallback failed: {e2}", 0)
                return False
        return False
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            await log_media_error("cleanup", f"Error cleaning temp directory: {e}")


# АВТОМАТИЧЕСКАЯ ИНТЕГРАЦИЯ В СУЩЕСТВУЮЩУЮ СИСТЕМУ
def integrate_corrector():
    """Автоматически интегрирует корректор в существующую систему"""
    try:
        import utils.rerate as rerate_module
        
        # Сохраняем оригинальную функцию
        if not hasattr(rerate_module, '_original_send_to_channel'):
            rerate_module._original_send_to_channel = rerate_module.send_to_channel
            
        # Заменяем на улучшенную версию
        rerate_module.send_to_channel = enhanced_send_to_channel
        
        logger.info("✅ Text corrector integrated successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to integrate text corrector: {e}")


# Автоматическая интеграция при импорте модуля
integrate_corrector()