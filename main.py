"""
title: Filter Pipeline
author: Vederis Leunardus
date: 2025-05-03
version: 1.0
license: MIT
description: Filter that works with mem0
requirements: requests
"""

from typing import List, Optional
from pydantic import BaseModel
from schemas import OpenAIChatMessage
from mem0 import MemoryClient

class Pipeline:
    class Valves(BaseModel):
        # List target pipeline ids (models) that this filter will be connected to.
        # If you want to connect this filter to all pipelines, you can set pipelines to ["*"]
        pipelines: List[str] = []

        # Assign a priority level to the filter pipeline.
        # The priority level determines the order in which the filter pipelines are executed.
        # The lower the number, the higher the priority.
        priority: int = 0

        client = MemoryClient(api_key="m0-*****8a5K") # put your API Key here
        user_id = "default_user" # change this incase needed the memory is linked to this user_id

        # Add your custom parameters here
        pass

    def __init__(self):
        # Pipeline filters are only compatible with Open WebUI
        # You can think of filter pipeline as a middleware that can be used to edit the form data before it is sent to the OpenAI API.
        self.type = "filter"

        # Optionally, you can set the id and name of the pipeline.
        # Best practice is to not specify the id so that it can be automatically inferred from the filename, so that users can install multiple versions of the same pipeline.
        # The identifier must be unique across all pipelines.
        # The identifier must be an alphanumeric string that can include underscores or hyphens. It cannot contain spaces, special characters, slashes, or backslashes.
        # self.id = "filter_pipeline"

        self.name = "mem0-owui"

        self.valves = self.Valves(**{"pipelines": ["llama3:latest"]})

        pass

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Inject memory context into the prompt before sending to the model."""
        print(f"inlet:{__name__}")

        # Extract messages from request body
        messages = body.get("messages", [])
        if not messages:
            return body

        # Determine user ID (prioritize request user, then valves default)
        current_user_id = self.valves.user_id
        if user and "id" in user:
            current_user_id = user["id"]

        # Find latest user message for memory query
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content")
                break

        if not user_message:
            return body

        try:
            # Retrieve relevant memories
            memories = self.valves.client.get_memories(
                user_id=current_user_id,
                query=user_message
            )

            # Inject memory context into system message
            if memories:
                memory_context = "\n\nRelevant memories:\n" + "\n".join(
                    f"- {mem['content']}" for mem in memories
                )
                
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
