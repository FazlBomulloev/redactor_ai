import os
import asyncio
import logging
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
        self.retry_errors = [
            FloodWaitError,
            ConnectionError,
            TimeoutError
        ]
        
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

    async def execute_with_retry(self, client_wrapper, operation_func, *args, **kwargs):
        """
        Выполнить операцию с повторными попытками и обработкой банов
        
        Args:
            client_wrapper: TelegramClientWrapper instance
            operation_func: Функция для выполнения (например, fetch_posts)
            *args, **kwargs: Аргументы для функции
        
        Returns:
            Результат операции или None при неудаче
        """
        current_account = client_wrapper.current_client_key
        
        for attempt in range(RETRY_ATTEMPTS):
            try:
                # Выполняем операцию
                result = await operation_func(*args, **kwargs)
                return result
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1}/{RETRY_ATTEMPTS} failed: {e}")
                
                # Если это бан - сразу удаляем аккаунт
                if self.is_ban_error(e):
                    await self.log_to_chat(
                        f"🚫 Account banned: {current_account} | Error: {type(e).__name__}",
                        "ERROR"
                    )
                    
                    # Удаляем аккаунт
                    await self.remove_account(current_account, f"banned: {type(e).__name__}")
                    
                    # Переключаемся на следующий аккаунт
                    try:
                        await client_wrapper.switch_to_next_account()
                        await self.log_to_chat(
                            f"🔄 Switched to next account: {client_wrapper.current_client_key}",
                            "INFO"
                        )
                        # Не делаем retry, возвращаем None для переключения
                        return None
                    except Exception as switch_error:
                        await self.log_to_chat(
                            f"❌ Failed to switch account: {str(switch_error)[:200]}",
                            "ERROR"
                        )
                        return None
                
                # Если это ошибка для retry
                elif self.is_retry_error(e) and attempt < RETRY_ATTEMPTS - 1:
                    await self.log_to_chat(
                        f"⏳ Retry {attempt + 1}/{RETRY_ATTEMPTS} in {RETRY_DELAY}s | Account: {current_account}",
                        "WARNING"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                
                # Если последняя попытка или неизвестная ошибка
                elif attempt == RETRY_ATTEMPTS - 1:
                    await self.log_to_chat(
                        f"❌ All retries failed for {current_account} | Error: {str(e)[:200]}",
                        "ERROR"
                    )
                    
                    # Переключаемся на следующий аккаунт
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
