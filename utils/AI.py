import ast
import asyncio
import os
from mistralai import Mistral
import json

api_key = "4nLSiw4wE9hV3zju2lSKl7yF0FhOLjb9"


client = Mistral(api_key=api_key)


async def AI(mess):
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
    return int(resp)
