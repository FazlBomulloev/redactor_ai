from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from core.models.ai_config import AIApiKey, AIAgent
from core.models.db_helper import db_helper
from core.repositories.base import BaseRepository


class AIApiKeyRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=AIApiKey)

    async def add(self, name: str, api_key: str, description: str = ""):
        async with self.db() as session:
            try:
                ai_key = AIApiKey(
                    name=name,
                    api_key=api_key,
                    description=description
                )
                session.add(ai_key)
                await session.commit()
                await session.refresh(ai_key)
                return ai_key
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to add AI API key: {e}")

    async def get_all_with_agents(self):
        """Получить все API ключи с их агентами"""
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(self.model).options(joinedload(self.model.agents))
                )
                return result.scalars().unique().all()
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get API keys with agents: {e}")

    async def delete_key(self, key_id: int):
        async with self.db() as session:
            try:
                # Сначала удаляем все связанные агенты
                stmt_agents = delete(AIAgent).where(AIAgent.api_key_id == key_id)
                await session.execute(stmt_agents)
                
                # Затем удаляем API ключ
                stmt = delete(self.model).where(self.model.id == key_id)
                await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to delete API key: {e}")


class AIAgentRepository(BaseRepository):
    def __init__(self):
        super().__init__(db=db_helper.session_getter, model=AIAgent)

    async def add(self, name: str, agent_id: str, api_key_id: int, description: str = ""):
        async with self.db() as session:
            try:
                agent = AIAgent(
                    name=name,
                    agent_id=agent_id,
                    api_key_id=api_key_id,
                    description=description
                )
                session.add(agent)
                await session.commit()
                await session.refresh(agent)
                return agent
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to add AI agent: {e}")

    async def get_all_with_api_keys(self):
        """Получить всех агентов с их API ключами"""
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(self.model).options(joinedload(self.model.api_key))
                )
                return result.scalars().all()
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get agents with API keys: {e}")

    async def delete_agent(self, agent_id: int):
        async with self.db() as session:
            try:
                stmt = delete(self.model).where(self.model.id == agent_id)
                await session.execute(stmt)
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise RuntimeError(f"Failed to delete agent: {e}")
                
    async def get_agents_by_api_key(self, api_key_id: int):
        """Получить всех агентов для конкретного API ключа"""
        async with self.db() as session:
            try:
                result = await session.execute(
                    select(self.model).where(self.model.api_key_id == api_key_id)
                )
                return result.scalars().all()
            except SQLAlchemyError as e:
                raise RuntimeError(f"Failed to get agents by API key: {e}")