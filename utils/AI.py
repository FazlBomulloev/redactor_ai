import ast
import asyncio
import os
from mistralai import Mistral
import json

api_key = "4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9"

client = Mistral(api_key=api_key)


async def AI(theme_and_message):
    """
    ОБНОВЛЕННАЯ функция для анализа сообщения с контекстом темы
    
    Args:
        theme_and_message: Строка содержащая контекст темы + сообщение
        или словарь с ключами 'theme' и 'message'
    """
    try:
        # Поддерживаем как строку, так и словарь
        if isinstance(theme_and_message, dict):
            if 'theme' in theme_and_message and 'message' in theme_and_message:
                prompt_content = f"""Оцени релевантность сообщения теме от 0 до 1. Верни только число.

{theme_and_message['theme']}

СООБЩЕНИЕ:
{theme_and_message['message']}

Оценка:"""
            else:
                # Fallback к старому формату
                prompt_content = f"Rate relevance 0-1. Return only decimal number. No text, no explanations, no percentages.\n\n{str(theme_and_message)}"
        else:
            # Если передана строка - используем её как есть (совместимость)
            prompt_content = f"Rate relevance 0-1. Return only decimal number. No text, no explanations, no percentages.\n\n{str(theme_and_message)}"

        chat_response = await client.agents.complete_async(
            agent_id="ag:55c24037:20241028:untitled-agent:701d2cd7",
            messages=[
                {
                    "role": "user",
                    "content": prompt_content,
                },
            ],
        )

        resp = chat_response.choices[0].message.content.strip()
        
        try:
            ratio = float(resp)
            if ratio > 1.0:
                ratio = ratio / 100.0
            ratio = max(0.0, min(1.0, ratio))
            return ratio
        except (ValueError, TypeError):
            print(f"Could not convert AI response to float: {resp}")
            return 0.0
            
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        return 0.0


async def AI_old(mess):
    """Старая функция - оставлена для совместимости"""
    chat_response = await client.agents.complete_async(
        agent_id="ag:55c24037:20241028:untitled-agent:701d2cd7",
        messages=[
            {
                "role": "user",
                "content": f"{mess}",
            },
        ],
    )

    resp = chat_response.choices[0].message.content
    try:
        return float(resp)
    except:
        return 0.0
