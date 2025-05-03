"""
title: mem0-owui-qdrant
author: Vederis Leunardus
date: 2025-05-03
version: 1.0
license: MIT
description: Filter that works with mem0
requirements: mem0ai, pydantic==2.11.4
"""

from typing import ClassVar, List, Optional
from pydantic import BaseModel
from schemas import OpenAIChatMessage
from mem0 import MemoryClient

class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = ["*"]
        priority: int = 0
        client: ClassVar[MemoryClient] = MemoryClient(api_key="put_api_key_here")  # ← Replace with your actual mem0 API key!
        user_id: str = "default_user"
        pass

    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves(**{"pipelines": ["*"]})
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
            print("DEBUG: MemoryClient initialized:", self.valves.client)
            print("DEBUG: Getting memories...")
            memories = self.valves.client.search(
                user_id=current_user_id,
                query=user_message
            )
            
            # Add current user message to memory
            self.valves.client.add(
                user_id=current_user_id,
                messages=[{"role": "user", "content": user_message}]
            )
            
            print("DEBUG: Retrieved memories:", memories)

            # Inject memory context into system message
            if memories:
                memory_context = "\n\nRelevant memories:\n" + "\n".join(
                    f"- {mem['memory']}" for mem in memories
                )
            else:
                # Initialize memory for new users
                try:
                    self.valves.client.add(
                        user_id=current_user_id,
                        messages="System: This is a new user conversation"
                    )
                    # Set default context after initialization
                    memory_context = "\n\nDefault memory initialized for new user conversation"
                except Exception as e:
                    print(f"Memory initialization failed: {str(e)}")
                    memory_context = ""  # Fallback to empty context

            # Add LLM memory generation instructions
            memory_context += "\n\nAlso, generate a concise memory summary of this interaction for future reference."
            
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

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Process LLM-generated memory from response"""
        print("DEBUG: Outlet method triggered")
        try:
            messages = body.get("messages", [])
            assistant_response = next((msg["content"] for msg in reversed(messages) if msg.get("role") == "assistant"), None)
            
            if assistant_response:
                # Extract memory content from response (look for specific memory markers)
                memory_start = assistant_response.find("MEMORY_SUMMARY_START")
                memory_end = assistant_response.find("MEMORY_SUMMARY_END")
                
                if memory_start != -1 and memory_end != -1:
                    memory_content = assistant_response[memory_start + len("MEMORY_SUMMARY_START"):memory_end].strip()
                    # Add basic validation for memory content
                    if len(memory_content) > 20:  # Simple quality check
                        current_user_id = user["id"] if user and "id" in user else self.valves.user_id
                        self.valves.client.add(
                            user_id=current_user_id,
                            messages=[{"role": "system", "content": memory_content}],
                            metadata={"type": "generated_memory"},
                            infer=False
                        )
                        print(f"Stored LLM-generated memory: {memory_content[:50]}...")
        except Exception as e:
            print(f"Memory storage error: {str(e)}")
            
        return body
