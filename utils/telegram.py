import asyncio
import logging
from datetime import datetime, timezone, timedelta
import time

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from telethon.tl.types import MessageMediaDocument, DocumentAttributeVideo, BotApp
from telethon.utils import resolve_bot_file_id
from mistralai import Mistral

from core.config import settings, reload_settings
from core.repositories.thematic_block import ThematicBlockRepository
from core.repositories.article import ArticleRepository
from utils.rerate import main_rer
from utils.telethon import TelegramClientWrapper, telegram_client_wrapper

# Импортируем AccountManager
from utils.account_manager import account_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация репозиториев и модели
repo = ThematicBlockRepository()
repo_art = ArticleRepository()

def get_target_chat_id():
    """Получает актуальный target_chat_id из настроек"""
    from core.config import settings
    return settings.channel__link

target_chat_id_test = -1002597796340

telegramClient = telegram_client_wrapper

# Настройки AI-агента
api_key = "4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9"
client_ai = Mistral(api_key=api_key)
MAX_VIDEO_SIZE_MB = 19
bot = Bot("8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw")


MISTRAL_REQUEST_DELAY = 0.15  
last_mistral_request_time = 0


async def safe_send_notification(message, max_retries=3):
    """Безопасная отправка уведомлений с обработкой rate limits"""
    for attempt in range(max_retries):
        try:
            await bot.send_message(target_chat_id_test, message)
            return True
        except TelegramRetryAfter as e:
            if attempt < max_retries - 1:
                logger.warning(f"Rate limit hit, waiting {e.retry_after} seconds")
                await asyncio.sleep(e.retry_after)
            else:
                logger.error(f"Failed to send notification after {max_retries} attempts")
                return False
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    return False


async def fetch_posts(client_wrapper, id):
    """Получение постов с интеграцией AccountManager"""
    
    # Нормализуем ID - может быть строка, число или список
    if isinstance(id, list):
        tb_ids = [str(i).strip() for i in id if str(i).strip()]  # Очищаем и конвертируем
    else:
        tb_ids = [str(id).strip()] if str(id).strip() else []
    
    if not tb_ids:
        logger.error("No valid IDs provided for fetch_posts")
        return [], []
    
    async def _fetch_posts_operation():
        """Внутренняя функция для выполнения операции"""
        all_sources = []
        all_stop_words = []
        
        # Обрабатываем каждый тематический блок
        for tb_id in tb_ids:
            try:
                tb = await repo.select_id(int(tb_id))
                if not tb:
                    logger.warning(f"No thematic block found with ID: {tb_id}")
                    continue
                    
                # Обрабатываем один ТБ (может быть объект или список)
                if isinstance(tb, list):
                    for item in tb:
                        # Очищаем пустые строки и лишние пробелы из источников
                        raw_sources = item.source.split(",") if item.source else []
                        clean_sources = [s.strip() for s in raw_sources if s.strip()]
                        all_sources.extend(clean_sources)
                        
                        # Очищаем стоп-слова
                        raw_stop_words = item.stop_words.split(",") if item.stop_words else []
                        clean_stop_words = [sw.strip() for sw in raw_stop_words if sw.strip()]
                        all_stop_words.extend(clean_stop_words)
                else:
                    # Очищаем пустые строки и лишние пробелы из источников
                    raw_sources = tb.source.split(",") if tb.source else []
                    clean_sources = [s.strip() for s in raw_sources if s.strip()]
                    all_sources.extend(clean_sources)
                    
                    # Очищаем стоп-слова
                    raw_stop_words = tb.stop_words.split(",") if tb.stop_words else []
                    clean_stop_words = [sw.strip() for sw in raw_stop_words if sw.strip()]
                    all_stop_words.extend(clean_stop_words)
                    
            except Exception as e:
                logger.error(f"Error processing TB {tb_id}: {e}")
                continue

        # Удаляем дубликаты источников и стоп-слов
        unique_sources = list(dict.fromkeys(all_sources))  # Сохраняем порядок
        unique_stop_words = list(dict.fromkeys(all_stop_words))

        if not unique_sources:
            logger.warning(f"No valid sources found for TBs {tb_ids}")
            return [], unique_stop_words

        messages = []
        logger.info(f"Fetching posts from sources: {unique_sources} for TBs {tb_ids}")
        await account_manager.log_to_chat(f"🔍 Fetching from {len(unique_sources)} sources for TBs {tb_ids}", "INFO")

        for source in unique_sources:
            count = 0
            try:
                # Используем безопасное получение сущности
                channel = await client_wrapper.safe_get_entity(source)
                logger.info(f"Channel details: {channel}")
                
                # Получаем time_back - используем максимальный из всех ТБ
                max_time_back = 900  # по умолчанию 15 часов
                for tb_id in tb_ids:
                    try:
                        tb = await repo.select_id(int(tb_id))
                        if tb:
                            if isinstance(tb, list):
                                for item in tb:
                                    if hasattr(item, 'time_back') and item.time_back:
                                        max_time_back = max(max_time_back, item.time_back)
                            else:
                                if hasattr(tb, 'time_back') and tb.time_back:
                                    max_time_back = max(max_time_back, tb.time_back)
                    except:
                        continue
                    
                offset_date = datetime.now(timezone.utc) - timedelta(minutes=max_time_back)
                logger.info(f"Fetching messages from {source} with offset_date: {offset_date} (time_back: {max_time_back}min)")
                
                try:
                    # Используем безопасную итерацию сообщений
                    async for message in client_wrapper.safe_iter_messages(
                        channel, 
                        offset_date=offset_date, 
                        reverse=True,
                        limit=50  # Ограничиваем количество сообщений
                    ):
                        try:
                            if message.date < offset_date:
                                logger.debug(f"Message {message.id} from {source} is older than offset_date.")
                                continue

                            # Если сообщение не содержит ни текста, ни медиа, пропускаем
                            if not message.text and not message.media:
                                logger.debug(f"Message {message.id} has no text or media, skipping")
                                continue

                            # Если сообщение содержит только медиа без текста, добавляем заглушку
                            if not message.text and message.media:
                                logger.info(f"Message {message.id} has media but no text, using media caption or placeholder")
                                # Можно использовать caption медиа или создать описание
                                if hasattr(message.media, 'caption') and message.media.caption:
                                    message.text = message.media.caption
                                else:
                                    message.text = "[Медиа без описания]"

                            # фильтрация по весу видео
                            if isinstance(message.media, MessageMediaDocument):
                                doc = message.media.document
                                is_video = any(isinstance(attr, DocumentAttributeVideo) for attr in doc.attributes)
                                if is_video:
                                    size_mb = doc.size / (1024 * 1024)
                                    if size_mb > MAX_VIDEO_SIZE_MB:
                                        logger.info(f"Skipped video {message.id} ({size_mb:.2f} MB) from {source} - exceeds {MAX_VIDEO_SIZE_MB} MB.")
                                        continue

                            messages.append(message)
                            count += 1
                            
                            # Ограничиваем количество сообщений на канал
                            if count >= 50:  # Максимум 50 сообщений с канала
                                break
                                
                        except Exception as msg_error:
                            logger.warning(f"Error processing message from {source}: {msg_error}")
                            continue
                            
                except Exception as iter_error:
                    logger.error(f"Error iterating messages from {source}: {iter_error}")
                    raise iter_error  # Перебрасываем ошибку для обработки в AccountManager

                logger.info(f"Fetched {count} messages from {source}")
                
            except Exception as e:
                # Проверяем, не является ли это ошибкой с пустой строкой
                if "Cannot find any entity corresponding to" in str(e) and ('""' in str(e) or source == ""):
                    logger.warning(f"Empty source detected, skipping: '{source}'")
                    continue
                    
                logger.error(f"Error fetching messages from {source}: {e}")
                raise e  # Перебрасываем ошибку для обработки в AccountManager

        logger.info(f"Fetched {len(messages)} messages from all sources for TBs {tb_ids}.")
        return messages, unique_stop_words
    
    # Выполняем операцию через AccountManager с retry логикой
    result = await account_manager.execute_with_retry(
        client_wrapper, 
        _fetch_posts_operation
    )
    
    if result is None:
        # Если операция не удалась после всех попыток
        logger.warning(f"Failed to fetch posts for TB {id} after all retries")
        await account_manager.log_to_chat(f"❌ Failed to fetch posts for TB {id}", "ERROR")
        return [], []
    
    messages, s_w = result
    await account_manager.log_to_chat(f"📥 Fetched {len(messages)} messages from all sources for TB {id}", "SUCCESS")
    return messages, s_w


def AI(mess, retries=3, delay=1):
    global last_mistral_request_time
    
    logger.info(f"Starting AI analysis for message: {str(mess)[:100]}...")
    
    # Проверяем, нужно ли ждать перед следующим запросом
    current_time = time.time()
    time_since_last_request = current_time - last_mistral_request_time
    
    if time_since_last_request < MISTRAL_REQUEST_DELAY:
        wait_time = MISTRAL_REQUEST_DELAY - time_since_last_request
        logger.info(f"Waiting {wait_time:.1f} seconds before next Mistral request...")
        time.sleep(wait_time)
    
    for attempt in range(retries):
        try:
            logger.info(f"Sending request to Mistral (attempt {attempt + 1})...")
            
            chat_response = client_ai.agents.complete(
                agent_id="ag:55c24037:20241028:untitled-agent:701d2cd7",
                messages=[
                    {
                        "role": "user", 
                        "content": f"Rate relevance 0-1. Return only decimal number. No text, no explanations, no percentages.\n\n{mess}",
                    },
                ],
            )
            
            # Обновляем время последнего запроса
            last_mistral_request_time = time.time()
            
            resp = chat_response.choices[0].message.content.strip()
            logger.info(f"AI raw response: {resp}")
            
            
            try:
                ratio = float(resp)
                
            
                if ratio > 1.0:
                    ratio = ratio / 100.0
                    logger.info(f"Normalized percentage to decimal: {ratio}")
                
                # Ограничиваем значение от 0 до 1
                ratio = max(0.0, min(1.0, ratio))
                
                logger.info(f"Final normalized ratio: {ratio}")
                return ratio
                
            except (ValueError, TypeError) as e:
                logger.error(f"Could not convert AI response to float: {resp}, error: {e}")
                return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            if attempt < retries - 1:
                wait_time = delay * (2**attempt)
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max retries reached for message: {mess}")
                return 0.0


async def get_all_matches(desc, messages, ignore_duplicates=False):
    """Получает все подходящие сообщения, отсортированные по рейтингу"""
    copied_messages = {}
    if not ignore_duplicates:
        message_save = await repo_art.select_all()
        for mess in message_save:
            copied_messages[mess.chat_id] = mess.message_id
    
    matches = []
    
    logger.info(f"Analyzing {len(messages)} messages for matches")
    await account_manager.log_to_chat(f"🤖 Analyzing {len(messages)} messages with AI", "INFO")

    for message in messages:
        if not message.text or message.text == "":
            logger.debug(f"Message text is None or empty for message ID: {message.id}")
            continue

        try:
            # Вычисление сходства с помощью AI-агента
            ratio = AI(f"{desc.description}\n{message.text}")
            if ratio is None or ratio == 0.0:
                logger.debug(f"AI returned None or 0 for message ID: {message.id}")
                continue
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            continue

        logger.info(f"Message {message.id} from chat {message.peer_id.channel_id} has ratio {ratio:.3f} ({ratio*100:.1f}%)")
        
        # Проверяем, не было ли сообщение уже скопировано
        already_copied = False
        if not ignore_duplicates:
            for key, value in copied_messages.items():
                if key == message.peer_id.channel_id and value == message.id:
                    logger.debug(f"Message {message.id} from chat {message.peer_id.channel_id} already copied.")
                    already_copied = True
                    break
        
        
        if not already_copied and ratio >= 0.85:
            matches.append({
                'message': message,
                'ratio': ratio,
                'chat': message.peer_id.channel_id
            })
            logger.info(f"✅ Message {message.id} added to matches with {ratio:.3f} ({ratio*100:.1f}%)")
        else:
            if already_copied:
                logger.info(f"❌ Message {message.id} skipped - already copied")
            else:
                logger.info(f"❌ Message {message.id} skipped - rating {ratio:.3f} ({ratio*100:.1f}%) < 85%")

    # Сортируем по рейтингу (от большего к меньшему)
    matches.sort(key=lambda x: x['ratio'], reverse=True)
    
    logger.info(f"Found {len(matches)} potential matches with rating >= 85%")
    await account_manager.log_to_chat(f"🎯 Found {len(matches)} matches with rating >= 85%", "SUCCESS" if matches else "WARNING")
    return matches


async def copy_posts(
    client_wrapper, messages, target_chat_id, desc, stop_words, ignore_duplicates=False
):
    published = False
    attempts = 0
    max_attempts = 5  # Максимум 5 попыток
    
    logger.info(f"Starting copy_posts process with {len(messages)} messages")
    
    # Обрабатываем множественные тематические блоки
    if isinstance(desc, list):
        # Для списка описаний берем первое подходящее
        for item in desc:
            matches = await get_all_matches(item, messages, ignore_duplicates)
            
            for match in matches:
                if attempts >= max_attempts:
                    logger.warning(f"Reached maximum attempts ({max_attempts})")
                    await account_manager.log_to_chat(f"⚠️ Reached max attempts ({max_attempts})", "WARNING")
                    break
                    
                if match['ratio'] >= 0.85:  
                    attempts += 1
                    success = await try_publish_message(
                        client_wrapper, match, target_chat_id, stop_words, attempts
                    )
                    if success:
                        published = True
                        break
                        
            if published:
                break
    else:
        # Один тематический блок
        matches = await get_all_matches(desc, messages, ignore_duplicates)
        
        for match in matches:
            if attempts >= max_attempts:
                logger.warning(f"Reached maximum attempts ({max_attempts})")
                await account_manager.log_to_chat(f"⚠️ Reached max attempts ({max_attempts})", "WARNING")
                break
                
            if match['ratio'] >= 0.85:  # СТРОГО 85% и выше
                attempts += 1
                success = await try_publish_message(
                    client_wrapper, match, target_chat_id, stop_words, attempts
                )
                if success:
                    published = True
                    break
    
    if not published:
        logger.warning(f"No suitable messages found for publication with rating >= 85% after {attempts} attempts")
        await account_manager.log_to_chat(f"❌ No messages published after {attempts} attempts", "ERROR")


async def try_publish_message(client_wrapper, match, target_chat_id, stop_words, attempt_num):
    """Пытается опубликовать сообщение, возвращает True при успехе"""
    message_id = match['message'].id
    try:
        logger.info(f"Attempt {attempt_num}: Publishing message {message_id} with ratio {match['ratio']:.3f} ({match['ratio']*100:.1f}%)")
        
        # Получаем безопасный клиент для копирования
        safe_client = await client_wrapper.get_current_client_safe()
        
        # Пытаемся обработать и отправить сообщение
        success = await main_rer(match['message'], target_chat_id, safe_client, stop_words)
        
        # Если отправка прошла успешно, добавляем в репозиторий
        if success:
            await repo_art.add(message_id, match['chat'], match['message'].text, datetime.now())
            logger.info(f"Successfully published message {message_id} to {target_chat_id}")
            await account_manager.log_to_chat(f"✅ Published message {message_id} with {match['ratio']:.3f} ratio", "SUCCESS")
            return True
        else:
            logger.warning(f"Message {message_id} was filtered out, trying next message")
            return False
            
    except Exception as e:
        logger.error(f"Error publishing message {message_id}: {e}")
        await account_manager.log_to_chat(f"❌ Publish error for {message_id}: {str(e)[:200]}", "ERROR")
        return False


async def main(id, ignore_duplicates=False):
    try:
        # Нормализуем ID для логирования
        display_id = id if not isinstance(id, list) else f"[{','.join(map(str, id))}]"
        logger.info(f"Starting main function for thematic block(s) ID: {display_id}")
        await account_manager.log_to_chat(f"🚀 Starting TB {display_id} processing", "INFO")
        
        # Используем client_wrapper вместо прямого обращения к клиенту
        messages, s_w = await fetch_posts(telegramClient, id)
        
        if not messages:
            logger.warning(f"No messages found for thematic block(s) ID: {display_id}")
            await account_manager.log_to_chat(f"⚠️ No messages found for TB {display_id}", "WARNING")
            return
            
        logger.info(f"Found {len(messages)} messages, processing...")
        
        # Получаем описания для всех тематических блоков
        tb_descriptions = []
        tb_ids = id if isinstance(id, list) else [id]
        
        for tb_id in tb_ids:
            try:
                tb_desc = await repo.select_id(int(str(tb_id).strip()))
                if tb_desc:
                    if isinstance(tb_desc, list):
                        tb_descriptions.extend(tb_desc)
                    else:
                        tb_descriptions.append(tb_desc)
            except Exception as e:
                logger.error(f"Error getting description for TB {tb_id}: {e}")
                continue
        
        if not tb_descriptions:
            logger.warning(f"No valid descriptions found for TB {display_id}")
            await account_manager.log_to_chat(f"⚠️ No descriptions found for TB {display_id}", "WARNING")
            return
        
        await copy_posts(
            telegramClient,
            messages,
            get_target_chat_id(),  
            tb_descriptions,  # Передаем все описания
            s_w,
            ignore_duplicates,
        )
        
        logger.info(f"Successfully processed thematic block(s) ID: {display_id}")
        await account_manager.log_to_chat(f"✅ Completed TB {display_id} processing", "SUCCESS")
        
    except Exception as e:
        display_id = id if not isinstance(id, list) else f"[{','.join(map(str, id))}]"
        logger.error(f"Error in main function for thematic block(s) ID {display_id}: {e}")
        await account_manager.log_to_chat(f"❌ TB {display_id} error: {str(e)[:200]}", "ERROR")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


async def publish_article(article):
    """Публикация статьи с улучшенной обработкой медиа"""
    try:
        logger.info(f"Publishing individual article ID: {article.id}")
        await account_manager.log_to_chat(f"📝 Publishing individual article {article.id}", "INFO")
        
        # Используем безопасный клиент для публикации
        safe_client = await telegramClient.get_current_client_safe()
        
        if article.media:
            logger.info(f"Article {article.id} has media: {article.media[:20]}...")
            # Определяем тип медиа и отправляем соответственно
            if article.media.startswith("AgAC"):  # Фото
                await safe_client.send_file(
                    get_target_chat_id(), 
                    article.media,
                    caption=article.text
                )
                logger.info(f"Sent article {article.id} as photo")
            elif article.media.startswith("BAAC"):  # Видео
                await safe_client.send_file(
                    get_target_chat_id(),  
                    article.media,
                    caption=article.text
                )
                logger.info(f"Sent article {article.id} as video")
            else:
                # Если тип медиа неизвестен, отправляем только текст
                await safe_client.send_message(
                    get_target_chat_id(),  
                    article.text
                )
                logger.warning(f"Unknown media type for article {article.id}, sent as text")
        else:
            await safe_client.send_message(
                get_target_chat_id(),  
                article.text
            )
            logger.info(f"Sent article {article.id} as text-only")
            
        await account_manager.log_to_chat(f"✅ Published individual article {article.id}", "SUCCESS")
        logger.info(f"Successfully published article ID: {article.id}")
            
    except Exception as e:
        logger.error(f"Error publishing article: {e}")
        await account_manager.log_to_chat(f"❌ Article {article.id} error: {str(e)[:200]}", "ERROR")
        
        try:
            safe_client = await telegramClient.get_current_client_safe()
            await safe_client.send_message(
                get_target_chat_id(),  
                article.text
            )
            logger.info(f"Published article ID: {article.id} as text-only after media error")
            await account_manager.log_to_chat(f"📝 Article {article.id} sent as fallback text", "SUCCESS")
        except Exception as e2:
            logger.error(f"Error sending text-only message: {e2}")
            await account_manager.log_to_chat(f"❌ Article {article.id} complete failure: {str(e2)[:200]}", "ERROR")


async def update_target_chat_id():
    """Обновляет target_chat_id из настроек"""
    reload_settings()
    logger.info(f"Updated target_chat_id to: {get_target_chat_id()}")
    await account_manager.log_to_chat(f"🔄 Target chat updated to: {get_target_chat_id()}", "INFO")
