import asyncio
import logging
from datetime import datetime, timezone, timedelta
import time

from mistralai import Mistral
from sentence_transformers import SentenceTransformer, util

from core.config import settings
from core.repositories.event import EventRepository
from core.repositories.article import ArticleRepository
from utils.rerate import main_rer
from utils.telethon import TelegramClientWrapper, telegram_client_wrapper
repo = EventRepository()
repo_art = ArticleRepository()

def get_target_chat_id_events():
    """Получает актуальный target_chat_id из настроек для events"""
    from core.config import settings
    return settings.channel__link

telegramClient = telegram_client_wrapper

api_key = "4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9"
client_ai = Mistral(api_key=api_key)


MISTRAL_REQUEST_DELAY = 0.25  
last_mistral_request_time_events = 0

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def calculate_minutes_between_times(start_time_str, end_time_str):
    def parse_time(time_str):
        return datetime.strptime(time_str, "%H:%M")

    start_time = parse_time(start_time_str)
    end_time = parse_time(end_time_str)
    time_difference = end_time - start_time
    if time_difference.total_seconds() < 0:
        time_difference += timedelta(days=1)
    minutes_difference = time_difference.total_seconds() / 60
    return minutes_difference


async def fetch_posts(client_wrapper, id):
    ev = await repo.select_id(id)
    sources = []
    if isinstance(ev, list):
        for item in ev:
            sources.extend(item.source.split(","))
    else:
        sources.extend(ev.source.split(","))
    minutes = int(ev.interval) + 20
    messages_txt = {}
    messages = {}
    logger.info(f"Fetching posts from sources: {sources}")

    for source in sources:
        try:
            # Используем безопасное получение сущности
            channel = await client_wrapper.safe_get_entity(source)
            logger.info(f"Channel details: {channel}")
            
            try:
                # Используем безопасную итерацию сообщений
                async for message in client_wrapper.safe_iter_messages(
                    channel,
                    offset_date=datetime.now(timezone.utc) - timedelta(minutes=minutes),
                    reverse=True,
                    limit=5  # Ограничиваем количество сообщений
                ):
                    try:
                        if not message.text:
                            logger.debug(f"Message {message.id} has no text, skipping")
                            continue
                            
                        messages_txt[channel.id] = message.text
                        messages[channel.id] = message
                        break  # Берем только одно сообщение для events
                        
                    except Exception as msg_error:
                        logger.warning(f"Error processing message {message.id}: {msg_error}")
                        continue
                        
            except Exception as iter_error:
                logger.error(f"Error iterating messages from {source}: {iter_error}")
                    
            logger.info(f"Fetched messages from {source}")
            
        except Exception as e:
            logger.error(f"Error fetching messages from {source}: {e}")
            continue

    logger.info(f"Fetched {len(messages)} messages from all sources.")
    return messages, messages_txt


def AI(mess, retries=5, delay=2):
    global last_mistral_request_time_events
    
    logger.info(f"Sending to AI: {str(mess)[:100]}...")
    
    # Проверяем, нужно ли ждать перед следующим запросом
    current_time = time.time()
    time_since_last_request = current_time - last_mistral_request_time_events
    
    if time_since_last_request < MISTRAL_REQUEST_DELAY:
        wait_time = MISTRAL_REQUEST_DELAY - time_since_last_request
        logger.info(f"Waiting {wait_time:.1f} seconds before next Mistral request...")
        time.sleep(wait_time)
    
    for attempt in range(retries):
        try:
            logger.info(f"Sending request to Mistral (attempt {attempt + 1})...")
            
            # Преобразуем словарь в строку для AI
            if isinstance(mess, dict):
                mess_str = "\n".join([f"{k}: {v[:200]}..." if len(str(v)) > 200 else f"{k}: {v}" for k, v in mess.items()])
            else:
                mess_str = str(mess)
                
            chat_response = client_ai.agents.complete(
                agent_id="ag:55c24037:20240929:untitled-agent:472eca29",
                messages=[
                    {
                        "role": "user",
                        "content": f"Выбери лучшее сообщение из предложенных по ID канала. Верни только ID канала (число): {mess_str}",
                    },
                ],
            )
            
            # Обновляем время последнего запроса
            last_mistral_request_time_events = time.time()
            
            resp = chat_response.choices[0].message.content.strip()
            logger.info(f"AI response: {resp}")
            
            # Попытка извлечь число из ответа
            import re
            numbers = re.findall(r'\d+', resp)
            if numbers:
                return int(numbers[0])
            else:
                logger.warning(f"No number found in AI response: {resp}")
                return 0
                
        except Exception as e:
            logger.error(f"Error in AI call (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                wait_time = delay * (2**attempt)
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for AI call")
                return 0


async def best_msg(messages, messages_txt):
    mess = AI(messages_txt)
    logger.info(f"AI details: {mess}")
    if mess is None:
        logger.error("AI returned None")
        return None
    if int(mess) == 0:
        return 0
    else:
        return messages[int(mess)]


async def copy_posts(client, message, target_chat_id):
    try:
        target_chat = await client.get_entity(target_chat_id)
        logger.info(f"Target chat details: {target_chat}")
        await main_rer(message, target_chat, client)
        logger.info(f"Copied post {message.id} to {target_chat_id}")
    except Exception as e:
        logger.error(f"Error copying post {message.id}: {e}")


async def main(id, ignore_duplicates=False):
    try:
        logger.info(f"Starting main function for event ID: {id}")
        messages, messages_txt = await fetch_posts(telegramClient, id)
        
        if not messages or not messages_txt:
            logger.warning(f"No messages found for event ID: {id}")
            return
            
        logger.info(f"Found {len(messages)} messages, processing with AI...")
        mess = await best_msg(messages, messages_txt)
        
        if mess is None:
            logger.error("AI returned None - no suitable message found")
            return
        if mess == 0:
            logger.info("AI returned 0 - no message to publish")
            return
            
        logger.info(f"AI selected message ID: {mess.id}, attempting to copy...")
        await copy_posts(
            telegramClient.get_current_client(),
            mess,
            get_target_chat_id_events(), 
        )
        logger.info(f"Successfully processed and published message for event ID: {id}")
        
    except Exception as e:
        logger.error(f"Error in main function for event ID {id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")