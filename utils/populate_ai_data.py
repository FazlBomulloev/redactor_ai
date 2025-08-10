# utils/populate_ai_data.py
"""
Скрипт для заполнения базы данных дефолтными ИИ настройками
Запустить один раз после создания таблиц
"""
import asyncio
from core.repositories.ai_config import AIApiKeyRepository, AIAgentRepository


async def populate_ai_data():
    """Заполняет базу дефолтными данными для ИИ"""
    api_key_repo = AIApiKeyRepository()
    agent_repo = AIAgentRepository()
    
    try:
        # Добавляем основной API ключ
        print("Adding default API key...")
        api_key = await api_key_repo.add(
            name="Main API Key",
            api_key="4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9",
            description="Primary Mistral API key"
        )
        
        # Добавляем агентов с привязкой к API ключу
        agents_data = [
            {
                "name": "Original Agent",
                "agent_id": "ag:55c24037:20241028:untitled-agent:701d2cd7",
                "description": "Original content analysis agent"
            },
            {
                "name": "Redactor 1",
                "agent_id": "ag:9885ec37:20250720:redactor1:5dacb8af",
                "description": "Additional content analysis agent #1"
            },
            {
                "name": "Redactor 2", 
                "agent_id": "ag:9885ec37:20250720:redactor2:6d68cfdd",
                "description": "Additional content analysis agent #2"
            },
            {
                "name": "Redactor 3",
                "agent_id": "ag:9885ec37:20250720:redactor3-07:1f951206",
                "description": "Additional content analysis agent #3"
            }
        ]
        
        print("Adding default agents...")
        for agent_data in agents_data:
            await agent_repo.add(
                name=agent_data['name'],
                agent_id=agent_data['agent_id'],
                api_key_id=api_key.id,  # Привязываем к созданному API ключу
                description=agent_data['description']
            )
            print(f"  - Added agent: {agent_data['name']}")
        
        print("✅ Default AI data populated successfully!")
        print(f"✅ API Key: {api_key.name} (ID: {api_key.id})")
        print(f"✅ Agents: {len(agents_data)} agents added")
        
    except Exception as e:
        print(f"❌ Error populating AI data: {e}")


if __name__ == "__main__":
    asyncio.run(populate_ai_data())