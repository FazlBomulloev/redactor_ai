import asyncio
import os
import time
from pathlib import Path
from core.config import settings, reload_settings
import logging

# Используем стандартный логгер вместо импорта из logger.py
logger = logging.getLogger(__name__)

class ConfigWatcher:
    def __init__(self):
        self.env_file = Path(".env")
        self.last_modified = None
        self.current_channel = None
        
    async def start_watching(self):
        """Запуск мониторинга изменений конфигурации"""
        logger.info("Starting config watcher...")
        self.current_channel = settings.channel__link
        
        if self.env_file.exists():
            self.last_modified = self.env_file.stat().st_mtime
            
        while True:
            try:
                await self.check_config_changes()
                await asyncio.sleep(10)  # Проверяем каждые 10 секунд
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")
                await asyncio.sleep(30)
    
    async def check_config_changes(self):
        """Проверка изменений в конфигурации"""
        if not self.env_file.exists():
            return
            
        current_modified = self.env_file.stat().st_mtime
        
        if self.last_modified and current_modified > self.last_modified:
            logger.info("Config file changed, reloading settings...")
            
            # Перезагружаем настройки
            reload_settings()
            
            # Проверяем, изменился ли канал
            if settings.channel__link != self.current_channel:
                logger.info(f"Channel changed from {self.current_channel} to {settings.channel__link}")
                self.current_channel = settings.channel__link
                
                # Обновляем канал в telegram.py
                try:
                    from utils.telegram import update_target_chat_id
                    await update_target_chat_id()
                    logger.info("Target chat ID updated successfully")
                except Exception as e:
                    logger.error(f"Error updating target chat ID: {e}")
                
                # Перезапускаем планировщик
                try:
                    from utils.shedule import restart_scheduler
                    await restart_scheduler()
                    logger.info("Scheduler restarted successfully")
                except Exception as e:
                    logger.error(f"Error restarting scheduler: {e}")
                
            self.last_modified = current_modified

# Создаем экземпляр для импорта
config_watcher = ConfigWatcher()