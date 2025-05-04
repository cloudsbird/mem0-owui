"""
title: mem0-owui-self-hosted
author: Vederis Leunardus
date: 2025-05-03
version: 1.0
license: MIT
description: Filter that works with mem0
requirements: mem0ai==0.1.96, pydantic==2.7.4
"""

from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field, model_validator
from schemas import OpenAIChatMessage
from mem0 import Memory


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = ["*"]
        priority: int = 0
        user_id: str = "default_user"
        pass

    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves(**{"pipelines": ["*"]})
        print("initializing mem0 client")
        self.m = self.init_mem_zero()
        print("mem0 client initialized")
        pass

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Inject memory context into the prompt before sending to the model."""
        print("DEBUG: Inlet method triggered")

        print(f"Current module: {__name__}")
        print(f"Request body: {body.keys()}")
        if "metadata" in body:
            print(f"Request metadata: {body['metadata'].keys()}")
        print(f"Pipeline ID: {self.valves.pipelines}")

        messages = body.get("messages", [])
        if not messages or "task" in body["metadata"]:
            return body

        print(f"User object: {user}")
        current_user_id = self.valves.user_id

        if user and "id" in user:
            current_user_id = user["id"]
        print(f"Using user ID: {current_user_id}")

        # Find latest user message for memory query
        print("Messages structure:")
        for i, msg in enumerate(messages):
            print(f"Message {i}: {msg.get('role')} - {msg.get('content')[:50]}...")

        user_message = None
        assistant_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content")
                print(f"Found user message: {user_message[:50]}...")
                break

        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                assistant_message = msg.get("content")
                print(f"Found assistant message: {assistant_message[:50]}...")
                break

        if not user_message:
            return body

        try:
            # Retrieve relevant memories and update memory with current message
            print("DEBUG: MemoryClient initialized:", self.m)
            print("DEBUG: Getting memories...")
            memories = self.m.search(user_id=current_user_id, query=user_message)

            if assistant_message:
                self.m.add(
                    user_id=current_user_id,
                    messages=[
                        {"role": "assistant", "content": assistant_message},
                    ],
                )

            # Add current user message to memory
            self.m.add(
                user_id=current_user_id,
                messages=[
                    {"role": "user", "content": user_message},
                ],
            )

            print("DEBUG: Retrieved memories:", memories)

            # Inject memory context into system message
            if memories:
                memory_context = "\n\nRelevant memories:\n" + "\n".join(
                    f"- {mem['memory']}" for mem in memories["results"]
                )

            # Find or create system message
            system_message = next(
                (msg for msg in messages if msg["role"] == "system"), None
            )
            if system_message:
                system_message["content"] += memory_context
            else:
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": f"Use these memories to enhance your response:\n{memory_context}",
                    },
                )

            # Update body with modified messages
            body["messages"] = messages

        except Exception as e:
            print(f"Mem0 integration error: {str(e)}")

        return body

    def init_mem_zero(self):
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": "qdrant",
                    "port": "6333",
                    "collection_name": "mem1024",
                    "embedding_model_dims": 1024,
                    "on_disk": True,
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "api_key": "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",
                    "model": "meta-llama/llama-4-scout:nitro",
                    "openai_base_url": "https://openrouter.ai/api/v1",
                },
            },
            "embedder": {
                "provider": "lmstudio",
                "config": {
                    "lmstudio_base_url": "http://vllm:8000/v1",
                    "api_key": "eyJhbGciOiJIUzI1NiIsImtpZCI6IlV6SXJWd1h0dnprLVRvdzlLZWstc0M1akptWXBvX1VaVkxUZlpnMDRlOFUiLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJnaXRodWJ8ODY0MzQ1NyIsInNjb3BlIjoib3BlbmlkIG9mZmxpbmVfYWNjZXNzIiwiaXNzIjoiYXBpX2tleV9pc3N1ZXIiLCJhdWQiOlsiaHR0cHM6Ly9uZWJpdXMtaW5mZXJlbmNlLmV1LmF1dGgwLmNvbS9hcGkvdjIvIl0sImV4cCI6MTg5NjM2MzU0OSwidXVpZCI6ImMwZDA2MWQ3LWNhNzMtNDU1YS1iMTA4LWMwNjhjZDFmOGEyNCIsIm5hbWUiOiJPcGVuV2ViVUkiLCJleHBpcmVzX2F0IjoiMjAzMC0wMi0wM1QxNTozOTowOSswMDAwIn0.Ig4Kr8Szw6Sl5hFwZpZU2dVbP6IxdPP4N87_1BfBpEM",
                    "model": "BAAI/bge-m3",
                    "embedding_dims": "1024",
                },
            },
        }

        print("embeddings_dims")

        return Memory.from_config(config)

