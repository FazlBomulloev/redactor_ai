import os
import asyncio
import tempfile
from telethon import TelegramClient, __version__ as telethon_version
from telethon.errors import PhoneNumberBannedError, FloodWaitError, AuthKeyUnregisteredError
try:
    from telethon.errors import CDNFileHashMismatchError
except ImportError:
    class CDNFileHashMismatchError(Exception):
        pass
from telethon.tl.functions.messages import SendMediaRequest
from telethon.tl.types import InputMediaPhoto, InputMediaDocument, MessageMediaDocument, MessageMediaPhoto

from aiogram import Bot

from core.config import settings
ACCOUNTS_DIR = os.path.join(os.getcwd(), "accounts")

api_id = 26515046
api_hash = "22b6dbdfce28e71ce66911f29ccc5bfe"

super_adm = [6640814090, 817411344]
ADMIN_BOT_TOKEN = "6830235739:AAG0Bo5lnabU4hDVWlhPQmLtiMVePI2xRGg"
admin_bot = Bot(token=ADMIN_BOT_TOKEN)


class TelegramClientWrapper:
    def __init__(self):
        self.api_id = api_id
        self.api_hash = api_hash
        self.ACCOUNTS_DIR = os.path.join(os.getcwd(), "accounts")
        self._clients = {}
        self.current_client_key = None
        self.lock = asyncio.Lock()

        if not os.path.exists(self.ACCOUNTS_DIR):
            os.makedirs(self.ACCOUNTS_DIR)

    async def load_accounts(self):
        try:
            loaded_any = False
            for filename in os.listdir(self.ACCOUNTS_DIR):
                if filename.endswith(".session"):
                    try:
                        await self._try_add_account(filename)
                        loaded_any = True
                    except Exception as e:
                        print(f"[WARNING] Аккаунт {filename} не авторизован или ошибка: {e}")
            if not loaded_any:
                raise Exception("Нет доступных аккаунтов")
            self.current_client_key = list(self._clients.keys())[0]
            print(f"Loaded accounts: {len(self._clients)}")
            print(f"Current account: {self.current_client_key}")
        except Exception as e:
            print(f"[WARNING] {e}")
            await self.notify_admin_no_active_accounts()

    async def _try_add_account(self, session_name):
        session_path = os.path.join(self.ACCOUNTS_DIR, session_name)
        
        print(f"[INFO] Telethon version: {telethon_version}")
        
        # Для Telethon 1.37.0 пробуем разные варианты настроек
        client = None
        
        # Вариант 1: Пробуем с connection_retries и auto_reconnect
        try:
            client = TelegramClient(
                session_path, 
                self.api_id, 
                self.api_hash,
                connection_retries=3,
                auto_reconnect=True
            )
            print(f"[INFO] Created client with connection_retries for {session_name}")
        except TypeError:
            print(f"[INFO] connection_retries not supported, trying basic client")
            # Вариант 2: Базовый клиент
            try:
                client = TelegramClient(
                    session_path, 
                    self.api_id, 
                    self.api_hash
                )
                print(f"[INFO] Created basic client for {session_name}")
            except Exception as e:
                print(f"[ERROR] Failed to create client for {session_name}: {e}")
                raise e
        
        if client is None:
            raise Exception(f"Failed to create client for {session_name}")
        
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise Exception(f"Аккаунт {session_name} не авторизован")
        self._clients[session_name] = client
        print(f"[+] Аккаунт добавлен: {session_name}")

    async def watch_for_new_accounts(self):
        existing = set(os.listdir(self.ACCOUNTS_DIR))
        while True:
            await asyncio.sleep(15)
            current = set(os.listdir(self.ACCOUNTS_DIR))
            new_sessions = current - existing
            for session in new_sessions:
                if session.endswith(".session"):
                    try:
                        await self._try_add_account(session)
                        if not self.current_client_key:
                            self.current_client_key = session
                    except Exception as e:
                        print(f"[!] Ошибка добавления нового аккаунта: {e}")
            existing = current

    async def switch_to_next_account(self):
        """Переключиться на следующий аккаунт с уведомлением в логи"""
        from utils.account_manager import account_manager
        
        old_account = self.current_client_key
        
        if self.current_client_key:
            # Закрываем и удаляем текущий клиент
            client = self._clients.pop(self.current_client_key)
            try:
                await client.disconnect()
            except:
                pass  # Игнорируем ошибки при отключении
            
            # Удаляем файл сессии
            session_file = os.path.join(self.ACCOUNTS_DIR, self.current_client_key)
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                except:
                    pass  # Игнорируем ошибки удаления файла
            
            print(f"[!] Удалён аккаунт: {old_account}")

        if not self._clients:
            self.current_client_key = None
            await self.notify_admin_no_active_accounts()
            raise Exception("Нет доступных аккаунтов")

        self.current_client_key = list(self._clients.keys())[0]
        
        # Логируем переключение
        remaining_count = len(self._clients)
        await account_manager.log_to_chat(
            f"🔄 Switched account | Old: {old_account} | New: {self.current_client_key} | Remaining: {remaining_count}",
            "INFO"
        )
        
        print(f"[+] Переключен на: {self.current_client_key}")

    async def ensure_connected(self, client):
        """Убеждаемся, что клиент подключен"""
        try:
            if not client.is_connected():
                await client.connect()
        
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                raise Exception("Client is not authorized")
            
            return True
        except Exception as e:
            print(f"[!] Connection check failed: {e}")
            return False

    async def get_current_client_safe(self):
        """Получить текущий клиент с проверкой соединения"""
        if not self.current_client_key:
            raise Exception("Нет активного клиента")
    
        client = self._clients[self.current_client_key]
    
        if not await self.ensure_connected(client):
            # Попытка переключиться на следующий аккаунт
            await self.switch_to_next_account()
            client = self._clients[self.current_client_key]
            if not await self.ensure_connected(client):
                raise Exception("Не удалось подключиться ни к одному клиенту")
    
        return client

    async def safe_download_with_fallback(self, media, temp_dir=None, max_retries=3):
        """
        Безопасная загрузка медиа с fallback методами для Telethon 1.37.0
        """
        for attempt in range(max_retries):
            try:
                client = await self.get_current_client_safe()
                
                # Метод 1: Стандартная загрузка (попытка 0)
                if attempt == 0:
                    try:
                        path = await client.download_media(media, file=temp_dir)
                        if path and os.path.exists(path):
                            print(f"[+] Media downloaded successfully on attempt {attempt + 1}")
                            return path
                    except Exception as e:
                        error_str = str(e)
                        if ("cdn" in error_str.lower() or 
                            "Failed to get DC" in error_str or 
                            "hash mismatch" in error_str.lower() or
                            "203" in error_str):
                            print(f"[!] CDN error detected on attempt {attempt + 1}: {e}")
                            # Переходим к следующей попытке
                            await asyncio.sleep(1)
                            continue
                        # Для других ошибок - перебрасываем
                        raise
                
                # Метод 2: Повторная попытка с задержкой (попытка 1)
                elif attempt == 1:
                    print(f"[!] Retrying download with longer delay...")
                    await asyncio.sleep(3)
                    try:
                        path = await client.download_media(media, file=temp_dir)
                        if path and os.path.exists(path):
                            print(f"[+] Media downloaded on retry attempt {attempt + 1}")
                            return path
                    except Exception as e:
                        print(f"[!] Retry download failed: {e}")
                        await asyncio.sleep(2)
                        continue
                
                # Метод 3: Попытка с переключением аккаунта (попытка 2)
                else:
                    try:
                        print("[!] Trying with account switch...")
                        await self.switch_to_next_account()
                        new_client = await self.get_current_client_safe()
                        path = await new_client.download_media(media, file=temp_dir)
                        if path and os.path.exists(path):
                            print(f"[+] Media downloaded with new account")
                            return path
                    except Exception as e:
                        print(f"[!] Alternative account download failed: {e}")
                        break
                        
            except FloodWaitError as e:
                if attempt < max_retries - 1:
                    print(f"[!] Flood wait {e.seconds}s on attempt {attempt + 1}")
                    await asyncio.sleep(e.seconds)
                    continue
                break
            except Exception as e:
                print(f"[!] Download attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3 + attempt)  # Увеличиваем задержку
                    continue
                break
        
        print(f"[!] All download attempts failed for media")
        return None

    async def reconnect_current_client(self):
        """Переподключить текущий клиент"""
        if not self.current_client_key:
            return False
    
        try:
            client = self._clients[self.current_client_key]
            if client.is_connected():
                await client.disconnect()
        
            await asyncio.sleep(2)
            await client.connect()
        
            if await client.is_user_authorized():
                print(f"[+] Успешно переподключен: {self.current_client_key}")
                return True
            else:
                print(f"[!] Клиент не авторизован после переподключения: {self.current_client_key}")
                return False
            
        except Exception as e:
            print(f"[!] Ошибка переподключения: {e}")
            return False

    def get_current_client(self):
        if self.current_client_key:
            return self._clients[self.current_client_key]
        raise Exception("Нет активного клиента")

    async def send_message(self, chat_id, message, retry=True):
        async with self.lock:
            try:
                client = self.get_current_client()
                await client.send_message(chat_id, message)
            except Exception as e:
                print(f"[!] Ошибка отправки сообщения: {e}")
                try:
                    await self.switch_to_next_account()
                except Exception:
                    return  # Сообщение админу уже отправлено
                if retry:
                    await self.send_message(chat_id, message, retry=False)

    async def send_photo(self, chat_id, file_id, caption, retry=True):
        async with self.lock:
            try:
                client = self.get_current_client()
                media = InputMediaPhoto(file_id)
                await client(SendMediaRequest(chat_id, media=media, message=caption))
            except Exception as e:
                print(f"[!] Ошибка отправки фото: {e}")
                try:
                    await self.switch_to_next_account()
                except Exception:
                    return
                if retry:
                    await self.send_photo(chat_id, file_id, caption, retry=False)

    async def send_video(self, chat_id, file_id, caption, retry=True):
        async with self.lock:
            try:
                client = self.get_current_client()
                media = InputMediaDocument(file_id)
                await client(SendMediaRequest(chat_id, media=media, message=caption))
            except Exception as e:
                print(f"[!] Ошибка отправки видео: {e}")
                try:
                    await self.switch_to_next_account()
                except Exception:
                    return
                if retry:
                    await self.send_video(chat_id, file_id, caption, retry=False)

    async def notify_admin_no_active_accounts(self):
        try:
            for i in super_adm:
                await admin_bot.send_message(i, "❗ Нет активных Telegram-аккаунтов для отправки сообщений.")
        except Exception as e:
            print(f"[Ошибка при отправке админу]: {e}")

    async def disconnect_all(self):
        for client in self._clients.values():
            try:
                await client.disconnect()
            except:
                pass  # Игнорируем ошибки при отключении

    async def safe_get_entity(self, identifier, retries=3):
        """Безопасное получение сущности с обработкой через AccountManager"""
        from utils.account_manager import account_manager
        
        async def _get_entity():
            client = await self.get_current_client_safe()
            return await client.get_entity(identifier)
        
        # Используем account_manager для retry логики
        result = await account_manager.execute_with_retry(self, _get_entity)
        
        # Если результат None, значит произошло переключение аккаунта
        if result is None:
            # Пробуем еще раз с новым аккаунтом
            try:
                client = await self.get_current_client_safe()
                return await client.get_entity(identifier)
            except Exception as e:
                print(f"[!] Failed to get entity with new account: {e}")
                raise e
        
        return result

    async def safe_iter_messages(self, entity, **kwargs):
        """Безопасная итерация сообщений с обработкой через AccountManager"""
        from utils.account_manager import account_manager
        
        kwargs.setdefault('wait_time', 3)
        
        async def _iter_messages():
            client = await self.get_current_client_safe()
            messages = []
            async for message in client.iter_messages(entity, **kwargs):
                messages.append(message)
            return messages
        
        # Используем account_manager для retry логики
        result = await account_manager.execute_with_retry(self, _iter_messages)
        
        # Если результат None, значит произошло переключение аккаунта
        if result is None:
            # Пробуем еще раз с новым аккаунтом
            try:
                client = await self.get_current_client_safe()
                async for message in client.iter_messages(entity, **kwargs):
                    yield message
                return
            except Exception as e:
                print(f"[!] Failed to iterate messages with new account: {e}")
                return
        
        # Возвращаем сообщения
        for message in result:
            yield message

    def get_account_count(self):
        """Получить количество активных аккаунтов"""
        return len(self._clients)

    def get_account_list(self):
        """Получить список аккаунтов"""
        return list(self._clients.keys())

    async def remove_account_by_name(self, session_name: str):
        """Удалить аккаунт по имени"""
        if session_name in self._clients:
            client = self._clients.pop(session_name)
            try:
                await client.disconnect()
            except:
                pass
            
            # Удаляем файл
            session_path = os.path.join(self.ACCOUNTS_DIR, session_name)
            if os.path.exists(session_path):
                try:
                    os.remove(session_path)
                except:
                    pass
            
            # Если это был текущий аккаунт, переключаемся
            if self.current_client_key == session_name:
                if self._clients:
                    self.current_client_key = list(self._clients.keys())[0]
                else:
                    self.current_client_key = None
            
            return True
        return False

telegram_client_wrapper = TelegramClientWrapper()