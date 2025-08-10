import asyncio
import re
import shutil
import tempfile

import demoji
import os

from aiogram import Bot
from aiogram.types import InputFile, FSInputFile, InputMediaPhoto, InputMediaVideo
from moviepy.editor import VideoFileClip
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
)
from utils.telethon import TelegramClientWrapper
import utils.text_corrector
from core.repositories.stop_words import StopWordsRepository

# Импортируем только медиа логгер
from logger import (
    get_media_logger, log_media_start, log_media_group_found, 
    log_media_processing, log_media_download, log_media_skip, 
    log_media_final, log_send_start, log_send_method, 
    log_send_success, log_send_error, log_media_error
)

# Настройка логгера для медиа
media_logger = get_media_logger()

# Список слов для удаления
words_to_remove = ["слово1", "слово2", "слово3"]


def remove_emojis(text):
    return demoji.replace(text, "")


def remove_links_and_mentions(text):
    text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)
    text = re.sub(r"@\w+", "", text)
    return text


def replace_jargon(text):
    return text


def truncate_text(text, max_length):
    if len(text) > max_length:
        text = text[:max_length]
        # Убедимся, что не обрезаем посередине слова
        last_space = text.rfind(' ')
        if last_space > max_length * 0.8:  # Если пробел не слишком далеко от конца
            text = text[:last_space]
        text = text.rstrip('.,!?;:')  # Убираем знаки препинания в конце
    return text


def rewrite_last_paragraph(text, max_length):
    if len(text) <= max_length:
        return text

    paragraphs = text.split("\n")

    
    if len(text) > max_length:
        text = truncate_text(text, max_length)

    return text


def compress_video_to_size(input_path, output_path, target_size_mb):
    target_size_bytes = target_size_mb * 1024 * 1024
    clip = VideoFileClip(input_path)
    original_size = os.path.getsize(input_path)

    if original_size <= target_size_bytes:
        clip.close()
        return input_path  

    
    quality = 100
    while True:
        compressed_path = f"{output_path}_temp.mp4"
        clip.write_videofile(compressed_path, codec="libx264", bitrate=f"{quality}k")
        compressed_size = os.path.getsize(compressed_path)

        if compressed_size <= target_size_bytes:
            os.rename(compressed_path, output_path)
            clip.close()
            return output_path

        quality -= 5
        if quality <= 0:
            clip.close()
            raise ValueError("Не удалось сжать видео до целевого размера")


async def compress_video(media, client):
    # Скачиваем видео
    input_path = await client.download_media(media)
    output_path = input_path.replace(".mp4", "_compressed.mp4")

    # Сжимаем видео до 20 МБ
    compressed_path = compress_video_to_size(input_path, output_path, 20)

    # Отправляем сжатое видео
    compressed_video_message = await client.send_file("me", compressed_path)
    compressed_media = compressed_video_message.media

    # Удаляем временные файлы
    os.remove(input_path)
    os.remove(compressed_path)

    return compressed_media


async def get_message_media_group(client, message):
    """
    Получает все медиа файлы из группы сообщений (альбома)
    """
    media_list = []
    message_id = getattr(message, 'id', 'unknown')

    # Если у сообщения есть grouped_id, это часть альбома
    if hasattr(message, 'grouped_id') and message.grouped_id:
        await log_media_group_found(message_id, message.grouped_id, "checking...")

        # Получаем все сообщения из этой группы
        try:
            # Получаем историю сообщений вокруг текущего сообщения
            messages = await client.get_messages(
                message.peer_id,
                limit=20,
                offset_id=message.id + 10
            )

            # Фильтруем сообщения с тем же grouped_id
            grouped_messages = [
                msg for msg in messages
                if hasattr(msg, 'grouped_id') and msg.grouped_id == message.grouped_id
            ]

            await log_media_group_found(message_id, message.grouped_id, len(grouped_messages))

            # Собираем все медиа из группы
            for msg in grouped_messages:
                if msg.media:
                    media_list.append(msg.media)

        except Exception as e:
            await log_media_error(message_id, f"Failed to get media group: {e}")
            
            if message.media:
                media_list.append(message.media)
    else:
        # Обычное сообщение с одним медиа
        if message.media:
            media_list.append(message.media)

    return media_list


async def process_media(media_list, client, message_id="unknown"):
    """
    Обрабатывает список медиа файлов
    """
    processed_media = []

    if not media_list:
        return processed_media

    # Логируем типы медиа
    media_types = []
    for media in media_list:
        if isinstance(media, MessageMediaPhoto):
            media_types.append("photo")
        elif isinstance(media, MessageMediaDocument):
            if media.document.mime_type.startswith("video/"):
                media_types.append("video")
            elif media.document.mime_type.startswith("image/"):
                media_types.append("image")
            else:
                media_types.append("document")
        else:
            media_types.append("unknown")
    
    await log_media_processing(message_id, len(media_list), ", ".join(media_types))

    for i, media in enumerate(media_list):
        try:
            if isinstance(media, MessageMediaPhoto):
                processed_media.append(media)
                await log_media_download(message_id, i + 1, "photo")
            elif isinstance(media, MessageMediaDocument):
                if media.document.mime_type.startswith("video/"):
                    size_mb = media.document.size / (1024 * 1024)
                    if media.document.size > 50 * 1024 * 1024:  # 50 MB
                        await log_media_skip(message_id, i + 1, f"video too large ({size_mb:.1f}MB)")
                        continue
                    processed_media.append(media)
                    await log_media_download(message_id, i + 1, "video", size_mb)
                elif media.document.mime_type.startswith("image/"):
                    processed_media.append(media)
                    await log_media_download(message_id, i + 1, "image")
                else:
                    await log_media_skip(message_id, i + 1, f"unsupported type: {media.document.mime_type}")
            elif isinstance(media, MessageMediaWebPage):
                await log_media_skip(message_id, i + 1, "webpage")
            else:
                await log_media_skip(message_id, i + 1, f"unknown type: {type(media)}")
        except Exception as e:
            await log_media_error(message_id, f"Error processing media {i + 1}: {e}")
            continue

    # Ограничиваем количество медиа
    if len(processed_media) > 3:
        await log_media_skip(message_id, "excess", f"too many files ({len(processed_media)}), limiting to 3")
        processed_media = processed_media[:3]

    return processed_media


def remove_words(text, words_to_remove):
    for word in words_to_remove:
        text = re.sub(r"\b" + re.escape(word) + r"\b", "", text, flags=re.IGNORECASE)
    return text


async def remove_words_from_db(text):
    """Улучшенная функция удаления стоп-слов из базы данных (ИСПРАВЛЕННАЯ)"""
    repo_stop_words = StopWordsRepository()
    stop_words = await repo_stop_words.get_all_words()

    original_text = text
    
    for word in stop_words:
        # 1. Удаляем точное совпадение (с эмодзи)
        text = re.sub(r'\b' + re.escape(word) + r'\b', '', text, flags=re.IGNORECASE)
        
        # 2. Удаляем версию без эмодзи
        clean_word = demoji.replace(word, "").strip()
        if clean_word and clean_word != word:
            text = re.sub(r'\b' + re.escape(clean_word) + r'\b', '', text, flags=re.IGNORECASE)
        
        # 3. Удаляем слово с различными знаками препинания (ТОЛЬКО в стоп-словах)
        word_no_punct = re.sub(r'[^\w\s]', '', word).strip()
        if word_no_punct and word_no_punct != word and len(word_no_punct) > 2:
            text = re.sub(r'\b' + re.escape(word_no_punct) + r'\b', '', text, flags=re.IGNORECASE)
        
        # 4. Специальная обработка для слов с эмодзи в разных позициях
        if any(c for c in word if ord(c) > 127):  # Если есть не-ASCII символы (эмодзи)
            # Разбиваем на части и пробуем удалить каждую
            parts = re.split(r'[^\w\s]', word)
            for part in parts:
                part = part.strip()
                if len(part) > 3:  # Только длинные значимые части
                    text = re.sub(r'\b' + re.escape(part) + r'\b', '', text, flags=re.IGNORECASE)
        
        
        if len(word) > 5:  
            text = re.sub(re.escape(word), '', text, flags=re.IGNORECASE)
            if clean_word and len(clean_word) > 5:
                text = re.sub(re.escape(clean_word), '', text, flags=re.IGNORECASE)
    
    #
    text = re.sub(r'\s+', ' ', text)  # Множественные пробелы в один
    
    
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([,.!?;:])\s+([,.!?;:])', r'\1\2', text)  
    
    text = re.sub(r'^\s+|\s+$', '', text) 
    
    return text


async def rewrite_message(message, client, stop_words=["|UGM|"]):
    message_id = getattr(message, 'id', 'unknown')
    text = message.message
    
    # Логируем начало обработки
    has_media = bool(message.media)
    text_length = len(text) if text else 0
    await log_media_start(message_id, has_media, text_length)

    # Пропускаем сообщения с текстом меньше 50 символов
    if len(text) < 50:
        return None, None

    # Удаляем смайлы и графические знаки
    text = remove_emojis(text)

    # Удаляем ссылки и упоминания других каналов
    text = remove_links_and_mentions(text)

    # Исправляем жаргоны
    text = replace_jargon(text)

    # Удаляем знаки <..>, <...>, <....>
    text = re.sub(r"<[.]+>", "", text)

    # Удаляем все слова, начинающиеся на знак #
    text = re.sub(r"\B#\w+", "", text)

    # Удаляем стоп-слова из базы данных (ИСПРАВЛЕННАЯ ВЕРСИЯ)
    text = await remove_words_from_db(text)

    # Удаляем определенные слова из параметра (локальные стоп-слова)
    text = remove_words(text, stop_words)

    # ДОБАВЛЕНО: финальная очистка текста
    text = re.sub(r'\s+', ' ', text)  # Убираем лишние пробелы
    text = text.strip()  # Убираем пробелы в начале и конце

    # Получаем все медиа файлы из группы (альбома)
    media_list = await get_message_media_group(client, message)

    if media_list:
        # Обрабатываем медиа
        processed_media = await process_media(media_list, client, message_id)
        await log_media_final(message_id, len(processed_media), len(text))
        return text, processed_media
    else:
        await log_media_final(message_id, 0, len(text))

        if re.search(r"часть \d+", text):
            return None, None  # Не публикуем сообщение

        return text, None


async def send_to_channel(text, media_list, channel_username, telethon_client,
                          bot_token="8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw"):
    import tempfile, shutil
    from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

    temp_dir = tempfile.mkdtemp(prefix="telethon_media_")
    media_paths = []
    
    text_length = len(text) if text else 0
    media_count = len(media_list) if media_list else 0
    
    await log_send_start(channel_username, text_length, media_count)

    try:
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


# Исправленная функция main_rer
async def main_rer(message, targ_chat, client, stop_words=[]):
    """
    Основная функция для обработки и отправки сообщения

    Args:
        message: Объект сообщения Telegram
        targ_chat: ID или username целевого чата
        client: Telegram клиент
        stop_words: Список стоп-слов для фильтрации

    Returns:
        bool: True если сообщение успешно отправлено, False если отфильтровано или ошибка
    """
    message_id = getattr(message, 'id', 'unknown')

    try:
        new_text, new_media_list = await rewrite_message(message, client, stop_words)

        if new_text or new_media_list:
            success = await send_to_channel(new_text, new_media_list, targ_chat, client)
            return success
        else:
            return False

    except Exception as e:
        await log_media_error(message_id, f"main_rer error: {e}")
        return False


# Пример использования
async def main():
    client = TelegramClientWrapper()

    # Пример сообщения
    message = ...  # Замените на реальное сообщение
    targ_chat = "target_channel_username"  # Замените на реальный канал

    await main_rer(message, targ_chat, client)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())