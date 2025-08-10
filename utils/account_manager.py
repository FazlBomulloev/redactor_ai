import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from telethon.errors import (
    PhoneNumberBannedError, 
    AuthKeyUnregisteredError,
    UserDeactivatedBanError,
    FloodWaitError,
    SessionPasswordNeededError,
    PhoneNumberInvalidError
)
from telethon.errors.common import TypeNotFoundError  
try:
    from telethon.errors import CDNFileHashMismatchError
except ImportError:
    # Создаем заглушку если ошибка не существует
    class CDNFileHashMismatchError(Exception):
        pass

from logger import log_media_error  # Используем медиа логгер для аккаунтов
from aiogram import Bot

# Настройки
ACCOUNTS_DIR = os.path.join(os.getcwd(), "accounts")
ADMIN_BOT_TOKEN = "8188098148:AAGwioCD56-NmmwCZau1RC6dZXnPOEQP6Fw"
LOG_CHAT_ID = -1002597796340
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # секунд


class AccountManager:
    def __init__(self):
        self.banned_errors = [
            PhoneNumberBannedError,
            AuthKeyUnregisteredError, 
            UserDeactivatedBanError,
            PhoneNumberInvalidError
        ]
        self.corruption_errors = [
            TypeNotFoundError,  # Ошибки коррупции протокола
        ]
        self.retry_errors = [
            FloodWaitError,
            ConnectionError,
            TimeoutError,
        ]
        # CDN ошибки будем определять по тексту
        
    async def log_to_chat(self, message, level="INFO"):
        """Отправка сообщения в чат логов"""
        try:
            bot = Bot(token=ADMIN_BOT_TOKEN)
            emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "SUCCESS": "✅"
            }
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"{emoji.get(level, '📝')} {timestamp} | {message}"
            
            if len(formatted_message) > 4000:
                formatted_message = formatted_message[:3900] + "...[cut]"
                
            await bot.send_message(LOG_CHAT_ID, formatted_message)
            await bot.session.close()
            
        except Exception as e:
            logging.error(f"Failed to send account log to chat: {e}")

    def get_account_list(self) -> List[str]:
        """Получить список всех аккаунтов"""
        if not os.path.exists(ACCOUNTS_DIR):
            return []
        
        accounts = []
        for filename in os.listdir(ACCOUNTS_DIR):
            if filename.endswith(".session"):
                accounts.append(filename)
        return accounts

    async def remove_account(self, session_filename: str, reason: str = "manual"):
        """Удалить аккаунт и логировать"""
        try:
            session_path = os.path.join(ACCOUNTS_DIR, session_filename)
            if os.path.exists(session_path):
                os.remove(session_path)
                
            remaining_accounts = len(self.get_account_list())
            
            await self.log_to_chat(
                f"🗑️ Account removed: {session_filename} | Reason: {reason} | Remaining: {remaining_accounts}",
                "WARNING"
            )
            
            logging.info(f"Account {session_filename} removed. Remaining: {remaining_accounts}")
            return True
            
        except Exception as e:
            await self.log_to_chat(f"❌ Failed to remove account {session_filename}: {str(e)[:200]}", "ERROR")
            return False

    def is_ban_error(self, error: Exception) -> bool:
        """Проверить, является ли ошибка банном"""
        error_str = str(error)
        
        # Не считаем ошибку пустой строки банном
        if "Cannot find any entity corresponding to" in error_str and ('""' in error_str or "to ''" in error_str):
            return False
            
        # Не считаем обычные ошибки доступа банном
        if "No result found for entity_id" in error_str:
            return False
            
        return any(isinstance(error, banned_error) for banned_error in self.banned_errors)

    def is_retry_error(self, error: Exception) -> bool:
        """Проверить, нужно ли повторять запрос"""
        return any(isinstance(error, retry_error) for retry_error in self.retry_errors)

    def is_corruption_error(self, error: Exception) -> bool:
        """Проверить, является ли ошибка коррупцией протокола"""
        error_str = str(error)
        return (
            any(isinstance(error, corruption_error) for corruption_error in self.corruption_errors) or
            "Could not find a matching Constructor ID" in error_str or
            "TypeNotFoundError" in error_str
        )

    def is_cdn_error(self, error: Exception) -> bool:
        """Проверить, является ли ошибка связанной с CDN"""
        error_str = str(error)
        return (
            "Failed to get DC" in error_str or
            "cdn" in error_str.lower() or
            "hash mismatch" in error_str.lower()
        )

    async def execute_with_retry(self, client_wrapper, operation_func, *args, **kwargs):
        """
        Выполнить операцию с повторными попытками и обработкой банов
        """
        current_account = client_wrapper.current_client_key
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                # Выполняем операцию
                result = await operation_func(*args, **kwargs)
                return result
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed: {e}")
                
                # Бан
                if self.is_ban_error(e):
                    await self.log_to_chat(
                        f"🚫 Account banned: {current_account} | Error: {type(e).__name__}",
                        "ERROR"
                    )
                    await self.remove_account(current_account, f"banned: {type(e).__name__}")
                    try:
                        await client_wrapper.switch_to_next_account()
                        await self.log_to_chat(
                            f"🔄 Switched to next account: {client_wrapper.current_client_key}",
                            "INFO"
                        )
                        return None
                    except Exception as switch_error:
                        await self.log_to_chat(
                            f"❌ Failed to switch account: {str(switch_error)[:200]}",
                            "ERROR"
                        )
                        return None

                # Ошибка коррупции протокола
                elif self.is_corruption_error(e):
                    await self.log_to_chat(
                        f"🔧 Protocol corruption detected: {current_account} | Error: {type(e).__name__}",
                        "ERROR"
                    )
                    try:
                        await client_wrapper.switch_to_next_account()
                        await self.log_to_chat(
                            f"🔄 Switched account due to corruption: {client_wrapper.current_client_key}",
                            "INFO"
                        )
                        return None
                    except Exception as switch_error:
                        await self.log_to_chat(
                            f"❌ Failed to switch account: {str(switch_error)[:200]}",
                            "ERROR"
                        )
                        return None

                # CDN ошибка
                elif self.is_cdn_error(e):
                    await self.log_to_chat(
                        f"📡 CDN error detected: {current_account} | Attempt {attempt + 1}/{RETRY_ATTEMPTS}",
                        "WARNING"
                    )
                    if attempt < RETRY_ATTEMPTS - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        await self.log_to_chat(
                            f"⏳ CDN retry in {wait_time}s | Account: {current_account}",
                            "WARNING"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                # Retry ошибка
                elif self.is_retry_error(e) and attempt < RETRY_ATTEMPTS - 1:
                    await self.log_to_chat(
                        f"⏳ Retry {attempt + 1}/{RETRY_ATTEMPTS} in {RETRY_DELAY}s | Account: {current_account}",
                        "WARNING"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue

                # Последняя попытка
                elif attempt == RETRY_ATTEMPTS - 1:
                    await self.log_to_chat(
                        f"❌ All retries failed for {current_account} | Error: {str(e)[:200]}",
                        "ERROR"
                    )
                    try:
                        await client_wrapper.switch_to_next_account()
                        await self.log_to_chat(
                            f"🔄 Switched to next account after retries: {client_wrapper.current_client_key}",
                            "INFO"
                        )
                    except Exception as switch_error:
                        await self.log_to_chat(
                            f"❌ Failed to switch after retries: {str(switch_error)[:200]}",
                            "ERROR"
                        )
                    return None
        
        return None

    async def get_account_stats(self) -> dict:
        """Получить статистику аккаунтов"""
        accounts = self.get_account_list()
        return {
            "total_accounts": len(accounts),
            "account_list": accounts,
            "accounts_dir": ACCOUNTS_DIR
        }


# Глобальный экземпляр менеджера
account_manager = AccountManager()
