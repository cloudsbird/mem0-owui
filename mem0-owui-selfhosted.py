"""
title: mem0-owui-self-hosted
author: Vederis Leunardus
date: 2025-05-03
version: 1.0
license: MIT
description: Filter that works with mem0
requirements: mem0ai, pydantic==2.11.4, langchain-neo4j, rank_bm25
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
        self.m = self.init_mem_zero()
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
        print(f"Pipeline ID: {self.valves.pipelines}")

        messages = body.get("messages", [])
        if not messages:
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
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content")
                print(f"Found user message: {user_message[:50]}...")
                break

        if not user_message:
            return body

        try:
            # Retrieve relevant memories and update memory with current message
            print("DEBUG: MemoryClient initialized:", self.m)
            print("DEBUG: Getting memories...")
            memories = self.m.search(
                user_id=current_user_id,
                query=user_message
            )
            
            # Add current user message to memory
            self.m.add(
                user_id=current_user_id,
                messages=[{"role": "user", "content": user_message}]
            )
            
            print("DEBUG: Retrieved memories:", memories)

            # Inject memory context into system message
            if memories:
                memory_context = "\n\nRelevant memories:\n" + "\n".join(
                    f"- {mem['memory']}" for mem in memories['results']
                )
            else:
                # Initialize memory for new users
                try:
                    self.m.add(
                        user_id=current_user_id,
                        messages=[{"role": "user", "content": "System: This is a new user conversation"}]
                    )
                    # Set default context after initialization
                    memory_context = "\n\nDefault memory initialized for new user conversation"
                except Exception as e:
                    print(f"Memory initialization failed: {str(e)}")
                    memory_context = ""  # Fallback to empty context

            # Find or create system message
            system_message = next((msg for msg in messages if msg["role"] == "system"), None)
            if system_message:
                system_message["content"] += memory_context
            else:
                messages.insert(0, {
                    "role": "system",
                    "content": f"Use these memories to enhance your response:\n{memory_context}"
                })
            
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
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "api_key": "open_ai_key",
                    "model":"select your own open ai model",
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "api_key": "open_ai_key",
                    "model":"select your own open ai model",
                },
            },
        }

        return Memory.from_config(config)