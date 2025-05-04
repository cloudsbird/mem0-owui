#!/usr/bin/env python3
"""
Ingest chat history from an Open WebUI JSON export file into mem0.

Reads configuration from environment variables similar to the mem0 pipeline filter.
"""

import argparse
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple

from mem0 import AsyncMemory


# --- Configuration (Read from Environment Variables) ---

# Vector store config
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "mem1024")
EMBEDDING_MODEL_DIMS = int(os.getenv("EMBEDDING_MODEL_DIMS", 1024))
ON_DISK = os.getenv("ON_DISK", "True").lower() == "true"

# LLM config
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "placeholder")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-4-scout:nitro")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")

# Embedder config
EMBEDDER_PROVIDER = os.getenv("EMBEDDER_PROVIDER", "lmstudio")
EMBEDDER_BASE_URL = os.getenv("EMBEDDER_BASE_URL", "http://localhost:8000/v1")
EMBEDDER_API_KEY = os.getenv("EMBEDDER_API_KEY", "placeholder")
EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "BAAI/bge-m3")


async def init_mem_zero() -> AsyncMemory:
    """Initializes and returns an AsyncMemory client based on environment config."""
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "host": QDRANT_HOST,
                "port": QDRANT_PORT,
                "collection_name": COLLECTION_NAME,
                "embedding_model_dims": EMBEDDING_MODEL_DIMS,
                "on_disk": ON_DISK,
            },
        },
        "llm": {
            "provider": LLM_PROVIDER,
            "config": {
                "api_key": LLM_API_KEY,
                "model": LLM_MODEL,
                "openai_base_url": LLM_BASE_URL,
            },
        },
        "embedder": {
            "provider": EMBEDDER_PROVIDER,
            "config": {
                "lmstudio_base_url": EMBEDDER_BASE_URL,
                "api_key": EMBEDDER_API_KEY,
                "model": EMBEDDER_MODEL,
                "embedding_dims": str(EMBEDDING_MODEL_DIMS),
            },
        },
    }
    print("Initializing mem0 client with config:")
    # Avoid printing sensitive keys like api_key directly
    print(
        f"  Vector Store: provider=qdrant, host={QDRANT_HOST}, port={QDRANT_PORT}, collection={COLLECTION_NAME}"
    )
    print(f"  LLM: provider={LLM_PROVIDER}, model={LLM_MODEL}, base_url={LLM_BASE_URL}")
    print(
        f"  Embedder: provider={EMBEDDER_PROVIDER}, model={EMBEDDER_MODEL}, base_url={EMBEDDER_BASE_URL}"
    )

    try:
        memory = await AsyncMemory.from_config(config)
        print("Mem0 client initialized successfully.")
        return memory
    except Exception as e:
        print(f"Error initializing mem0 client: {e}")
        raise


def extract_messages_and_user_id_from_json(
    file_path: str,
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """Loads JSON data, extracts user/assistant messages, and the user ID."""
    print(f"Loading chat history from {file_path}...")
    user_id = None
    all_messages = []
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return None, []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return None, []

    if not isinstance(data, list) or not data:
        print("Error: Expected JSON data to be a non-empty list of chat sessions.")
        return None, []

    print(f"Found {len(data)} chat session(s) in the export.")

    # Attempt to extract user_id from the first session
    try:
        user_id = data[0].get("user_id")
        if user_id:
            print(f"Extracted user_id: {user_id}")
        else:
            print("Warning: Could not find 'user_id' in the first session.")
    except (KeyError, IndexError):
        print("Warning: Could not access the first session or 'user_id' key.")

    for i, session in enumerate(data):
        try:
            # Ensure the session is a dictionary before accessing keys
            if not isinstance(session, dict):
                print(f"Warning: Session {i + 1} is not a dictionary. Skipping.")
                continue

            # Extract user_id if not already found (though typically it's per-session)
            # If consistency is needed, you might want to check if user_id differs across sessions.
            if not user_id and "user_id" in session:
                user_id = session["user_id"]
                print(f"Extracted user_id from session {i + 1}: {user_id}")
            messages_dict = session["chat"]["history"]["messages"]
            session_messages = []
            # Sort messages by timestamp to maintain order, assuming timestamp exists and is reliable
            sorted_message_items = sorted(
                messages_dict.items(), key=lambda item: item[1].get("timestamp", 0)
            )

            for _, msg_data in sorted_message_items:
                role = msg_data.get("role")
                content = msg_data.get("content")
                if role in ["user", "assistant"] and content:
                    session_messages.append({"role": role, "content": content})

            if session_messages:
                print(
                    f"  Extracted {len(session_messages)} user/assistant messages from session {i + 1}."
                )
                all_messages.extend(session_messages)
            else:
                print(f"  No user/assistant messages found in session {i + 1}.")

        except KeyError as e:
            print(
                f"Warning: Could not find expected key {e} in session {i + 1}. Skipping."
            )
        except Exception as e:
            print(f"Warning: Error processing session {i + 1}: {e}. Skipping.")

    print(f"Total extracted messages: {len(all_messages)}")
    return user_id, all_messages


async def main():
    parser = argparse.ArgumentParser(
        description="Ingest chat history from an Open WebUI JSON export into mem0."
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="Path to the Open WebUI JSON export file.",
    )
    args = parser.parse_args()

    user_id, messages = extract_messages_and_user_id_from_json(args.file)

    if not user_id:
        print("Could not extract user ID from the file. Exiting.")
        return

    if not messages:
        print("No messages extracted or file format error. Exiting.")
        return

    try:
        mem0_client = await init_mem_zero()
    except Exception:
        print("Failed to initialize mem0 client. Exiting.")
        return

    print(f"Ingesting {len(messages)} messages for user '{user_id}'...")
    try:
        # Consider batching if there are a very large number of messages
        await mem0_client.add(messages=messages, user_id=user_id)
        print("Ingestion complete.")
    except Exception as e:
        print(f"Error during mem0 ingestion: {e}")


if __name__ == "__main__":
    asyncio.run(main())
