"""
title: mem0-owui-self-hosted
author: Vederis Leunardus
date: 2025-05-03
version: 1.0
license: MIT
description: Filter that works with mem0
requirements: mem0ai==0.1.96, pydantic==2.7.4
"""

import os
from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field, model_validator
from schemas import OpenAIChatMessage
from mem0 import AsyncMemory
import asyncio


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = ["*"]
        priority: int = 0
        user_id: str = Field(
            default="default_user", description="Default user ID for memory operations"
        )

        # Vector store config
        qdrant_host: str = Field(
            default="qdrant", description="Qdrant vector database host"
        )
        qdrant_port: str = Field(
            default="6333", description="Qdrant vector database port"
        )
        collection_name: str = Field(
            default="mem1024", description="Qdrant collection name"
        )
        embedding_model_dims: int = Field(
            default=1024, description="Embedding model dimensions"
        )
        on_disk: bool = Field(default=True, description="Store vectors on disk")

        # LLM config
        llm_provider: str = Field(
            default="openai", description="LLM provider (openai, etc)"
        )
        llm_api_key: str = Field(default="placeholder", description="LLM API key")
        llm_model: str = Field(
            default="meta-llama/llama-4-scout:nitro", description="LLM model name"
        )
        llm_base_url: str = Field(
            default="https://openrouter.ai/api/v1", description="LLM API base URL"
        )

        # Embedder config
        embedder_provider: str = Field(
            default="lmstudio", description="Embedding provider"
        )
        embedder_base_url: str = Field(
            default="http://vllm:8000/v1", description="Embedding API base URL"
        )
        embedder_api_key: str = Field(
            default="placeholder", description="Embedding API key"
        )
        embedder_model: str = Field(
            default="BAAI/bge-m3", description="Embedding model name"
        )

    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        pass

    async def on_valves_updated(self):
        print("initializing mem0 client")
        print(self.valves)
        self.m = await self.init_mem_zero()
        print("mem0 client initialized")

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    async def add_message_to_mem0(self, user_id, message):
        await self.m.add(user_id=user_id, messages=[message])
        print(f"Added message to mem0: {message}")

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Inject memory context into the prompt before sending to the model."""

        if self.m is None:
            print("Initializing mem0 client")
            self.m = await self.init_mem_zero()

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
            memories = await self.m.search(user_id=current_user_id, query=user_message)

            if assistant_message:
                asyncio.create_task(
                    self.add_message_to_mem0(
                        current_user_id,
                        {"role": "assistant", "content": assistant_message},
                    )
                )

            # Add current user message to memory
            asyncio.create_task(
                self.add_message_to_mem0(
                    user_id=current_user_id,
                    message={"role": "user", "content": user_message},
                )
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

    async def init_mem_zero(self):
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": self.valves.qdrant_host,
                    "port": self.valves.qdrant_port,
                    "collection_name": self.valves.collection_name,
                    "embedding_model_dims": self.valves.embedding_model_dims,
                    "on_disk": self.valves.on_disk,
                },
            },
            "llm": {
                "provider": self.valves.llm_provider,
                "config": {
                    "api_key": self.valves.llm_api_key,
                    "model": self.valves.llm_model,
                    "openai_base_url": self.valves.llm_base_url,
                },
            },
            "embedder": {
                "provider": self.valves.embedder_provider,
                "config": {
                    "lmstudio_base_url": self.valves.embedder_base_url,
                    "api_key": self.valves.embedder_api_key,
                    "model": self.valves.embedder_model,
                    "embedding_dims": str(self.valves.embedding_model_dims),
                },
            },
        }

        print("Initializing memory with config:", config)
        return await AsyncMemory.from_config(config)
