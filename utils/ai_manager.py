# utils/ai_manager.py
import asyncio
import logging
import time
from typing import List, Dict, Optional, Tuple
from mistralai import Mistral

from core.repositories.ai_config import AIApiKeyRepository, AIAgentRepository
from utils.account_manager import account_manager

logger = logging.getLogger(__name__)

def format_thematic_block_context(tb_obj):
    """Формирует контекст тематического блока для ИИ (только описание темы)"""    
    context_parts = []
    
    if hasattr(tb_obj, 'name') and tb_obj.name:
        context_parts.append(f"ТЕМАТИЧЕСКИЙ БЛОК: {tb_obj.name}")
    
    
    if hasattr(tb_obj, 'description') and tb_obj.description:
        context_parts.append(f"ОПИСАНИЕ ТЕМЫ: {tb_obj.description}")
    
    return "\n".join(context_parts)


class AIAnalysisManager:
    def __init__(self):
        self.api_key_repo = AIApiKeyRepository()
        self.agent_repo = AIAgentRepository()
        self.clients: Dict[int, Mistral] = {}  # api_key_id -> client
        self.last_request_times: Dict[int, float] = {}
        self.lock = asyncio.Lock()
        
        # Настройки
        self.base_delay = 0.35  # Базовая задержка между запросами
        self.max_retries = 2
        self.retry_delay = 1
        
    async def initialize(self):
        """Инициализация клиентов и агентов"""
        try:
            # Получаем все API ключи с агентами
            api_keys = await self.api_key_repo.get_all_with_agents()
            if not api_keys:
                logger.error("No API keys found!")
                return False
                
            # Создаем клиенты для каждого API ключа
            for key_obj in api_keys:
                if key_obj.agents:  # Только если у ключа есть агенты
                    client = Mistral(api_key=key_obj.api_key)
                    self.clients[key_obj.id] = client
                    self.last_request_times[key_obj.id] = 0
                    logger.info(f"Initialized AI client: {key_obj.name} with {len(key_obj.agents)} agents")
                
            logger.info(f"AI Manager initialized with {len(self.clients)} API keys")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Manager: {e}")
            return False
    
    async def get_all_agents(self) -> List:
        """Получить список всех агентов с их API ключами"""
        return await self.agent_repo.get_all_with_api_keys()
    
    def distribute_messages_to_agents(self, messages: List, agents: List) -> Dict[str, List]:
        """Распределяет сообщения между агентами поровну"""
        if not agents or not messages:
            return {}
        
        agent_messages = {agent.agent_id: [] for agent in agents}
        
        messages_per_agent = len(messages) // len(agents)
        remainder = len(messages) % len(agents)
        
        start_idx = 0
        for i, agent in enumerate(agents):
            end_idx = start_idx + messages_per_agent + (1 if i < remainder else 0)
            agent_messages[agent.agent_id] = messages[start_idx:end_idx]
            start_idx = end_idx
            
            logger.info(f"Agent {agent.name} assigned {len(agent_messages[agent.agent_id])} messages")
        
        return agent_messages
    
    async def analyze_message_batch(self, agent, messages_data: List[Dict], theme_context: str) -> List[Tuple[int, float]]:
        """Анализирует пакет сообщений одним агентом"""
        api_key_id = agent.api_key_id
        if api_key_id not in self.clients:
            logger.error(f"No client available for API key ID: {api_key_id}")
            return []
        
        client = self.clients[api_key_id]
        results = []
        
        await account_manager.log_to_chat(
            f"🤖 Agent {agent.name} analyzing {len(messages_data)} messages", 
            "INFO"
        )
        
        for msg_data in messages_data:
            message_id = msg_data['id']
            message_text = msg_data['text']
            
            try:
                ratio = await self._analyze_single_message(
                    client, agent.agent_id, theme_context, message_text, api_key_id
                )
                results.append((message_id, ratio))
                
                logger.info(f"Agent {agent.name} - Message {message_id}: {ratio:.3f}")
                
            except Exception as e:
                logger.error(f"Error analyzing message {message_id} with agent {agent.name}: {e}")
                results.append((message_id, 0.0))
        
        await account_manager.log_to_chat(
            f"✅ Agent {agent.name} completed {len(results)} analyses", 
            "SUCCESS"
        )
        
        return results
    
    async def _analyze_single_message(self, client: Mistral, agent_id: str, theme_context: str, 
                                     message_text: str, api_key_id: int) -> float:
        """Анализирует одно сообщение с контекстом темы"""
        
        # Контроль частоты запросов
        async with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_times.get(api_key_id, 0)
            
            if time_since_last < self.base_delay:
                wait_time = self.base_delay - time_since_last
                await asyncio.sleep(wait_time)
        
        for attempt in range(self.max_retries):
            try:
                response = await client.agents.complete_async(
                    agent_id=agent_id,
                    messages=[{
                        "role": "user", 
                        "content": f"""Оцени релевантность сообщения теме от 0 до 1. Верни только число.

{theme_context}

СООБЩЕНИЕ:
{message_text}

Оценка:""",
                    }],
                )
                
                # Обновляем время последнего запроса
                self.last_request_times[api_key_id] = time.time()
                
                resp = response.choices[0].message.content.strip()
                
                try:
                    ratio = float(resp)
                    # Нормализуем если нужно
                    if ratio > 1.0:
                        ratio = ratio / 100.0
                    ratio = max(0.0, min(1.0, ratio))
                    return ratio
                    
                except (ValueError, TypeError):
                    logger.error(f"Could not convert AI response to float: {resp}")
                    return 0.0
                    
            except Exception as e:
                logger.error(f"Error in AI analysis (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                else:
                    return 0.0
        
        return 0.0
    
    async def analyze_messages_distributed(self, messages: List, theme_context: str) -> Dict[int, float]:
        """Основная функция анализа с распределением по агентам"""
        
        # Инициализируемся если нужно
        if not self.clients:
            success = await self.initialize()
            if not success:
                logger.error("Failed to initialize AI Manager")
                return {}
        
        # Получаем всех агентов
        agents = await self.get_all_agents()
        if not agents:
            logger.error("No agents found")
            return {}
        
        logger.info(f"Starting distributed analysis of {len(messages)} messages using {len(agents)} agents")
        logger.info(f"Theme context length: {len(theme_context)} chars")
        
        # Подготавливаем данные сообщений
        messages_data = []
        for msg in messages:
            if hasattr(msg, 'text') and msg.text:
                messages_data.append({
                    'id': msg.id,
                    'text': msg.text,
                    'message': msg
                })
        
        if not messages_data:
            logger.warning("No messages with text found")
            return {}
        
        # Распределяем сообщения между агентами
        agent_messages = self.distribute_messages_to_agents(messages_data, agents)
        
        # Запускаем анализ параллельно для всех агентов
        tasks = []
        for agent in agents:
            if agent.agent_id in agent_messages and agent_messages[agent.agent_id]:
                task = asyncio.create_task(
                    self.analyze_message_batch(
                        agent, 
                        agent_messages[agent.agent_id], 
                        theme_context  # Передаем упрощенный контекст темы
                    )
                )
                tasks.append(task)
        
        # Ждем результаты от всех агентов
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Объединяем результаты
        all_results = {}
        for results_list in results_lists:
            if isinstance(results_list, list):
                for message_id, ratio in results_list:
                    all_results[message_id] = ratio
            else:
                logger.error(f"Error in agent analysis: {results_list}")
        
        logger.info(f"Distributed analysis completed: {len(all_results)} results")
        await account_manager.log_to_chat(
            f"🎯 Distributed AI analysis completed: {len(all_results)} messages processed", 
            "SUCCESS"
        )
        
        return all_results
    
    async def reload_configuration(self):
        """Перезагружает конфигурацию агентов и API ключей"""
        logger.info("Reloading AI configuration...")
        
        # Очищаем старые данные
        self.clients.clear()
        self.last_request_times.clear()
        
        # Инициализируемся заново
        success = await self.initialize()
        if success:
            logger.info("AI configuration reloaded successfully")
            await account_manager.log_to_chat("🔄 AI configuration reloaded", "SUCCESS")
        else:
            logger.error("Failed to reload AI configuration")
            await account_manager.log_to_chat("❌ Failed to reload AI configuration", "ERROR")
        
        return success

# Глобальный экземпляр менеджера
ai_manager = AIAnalysisManager()
