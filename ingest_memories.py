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


def extract_sessions_from_json(
    file_path: str,
) -> List[Tuple[Optional[str], List[Dict[str, str]]]]:
    """Loads JSON data and extracts user ID and messages for each session."""
    print(f"Loading chat history from {file_path}...")
    sessions_data = []
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}")
        return []

    if not isinstance(data, list):
        print("Error: Expected JSON data to be a list of chat sessions.")
        return []

    if not data:
        print("Warning: JSON file contains an empty list. No sessions to process.")
        return []

    print(f"Found {len(data)} chat session(s) in the export.")

    for i, session in enumerate(data):
        session_user_id = None
        session_messages = []
        try:
            # Ensure the session is a dictionary before accessing keys
            if not isinstance(session, dict):
                print(f"Warning: Session {i + 1} is not a dictionary. Skipping.")
                continue

            # Extract user_id for this specific session
            session_user_id = session.get("user_id")
            if not session_user_id:
                print(f"Warning: Could not find 'user_id' in session {i + 1}. Skipping ingestion for this session.")
                continue # Skip if no user_id for this session
            messages_dict = session.get("chat", {}).get("history", {}).get("messages", {})
            if not messages_dict:
                print(f"Warning: No messages found in session {i + 1} under chat.history.messages. Skipping.")
                continue

            # Sort messages by timestamp to maintain order
            try:
                sorted_message_items = sorted(
                    messages_dict.items(), key=lambda item: item[1].get("timestamp", 0)
                )
            except AttributeError:
                 print(f"Warning: Messages in session {i + 1} are not in the expected format (dict of dicts). Skipping.")
                 continue

            for _, msg_data in sorted_message_items:
                if not isinstance(msg_data, dict):
                    print(f"Warning: Message data is not a dictionary in session {i + 1}. Skipping message.")
                    continue
                role = msg_data.get("role")
                content = msg_data.get("content")
                if role in ["user", "assistant"] and content:
                    session_messages.append({"role": role, "content": content})

            if session_user_id and session_messages:
                print(
                    f"  Prepared session {i + 1} for user '{session_user_id}' with {len(session_messages)} messages."
                )
                sessions_data.append((session_user_id, session_messages))
            elif session_user_id:
                 print(f"  No valid user/assistant messages extracted for session {i + 1} (User: {session_user_id}).")
            # Case where session_user_id was missing is handled earlier

        except KeyError as e:
            print(
                f"Warning: Could not find expected key {e} in session {i + 1}. Skipping this session."
            )
        except Exception as e:
            print(f"Warning: Error processing session {i + 1}: {e}. Skipping this session.")

    print(f"Successfully prepared {len(sessions_data)} sessions for ingestion.")
    return sessions_data


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

    extracted_sessions = extract_sessions_from_json(args.file)

    if not extracted_sessions:
        print("No valid sessions extracted from the file. Exiting.")
        return

    try:
        mem0_client = await init_mem_zero()
    except Exception:
        print("Failed to initialize mem0 client. Exiting.")
        return

    ingested_count = 0
    failed_count = 0
    for session_user_id, session_messages in extracted_sessions:
        # Double check, though extraction function should ensure these are present
        if not session_user_id or not session_messages:
            print("Skipping session due to missing user ID or messages (should not happen here).")
            failed_count += 1
            continue

        print(f"Ingesting session for user '{session_user_id}' ({len(session_messages)} messages)...")
        try:
            # Ingest messages for the current session
            await mem0_client.add(messages=session_messages, user_id=session_user_id)
            print(f"  Successfully ingested session for user '{session_user_id}'.")
            ingested_count += 1
        except Exception as e:
            print(f"  Error during mem0 ingestion for user '{session_user_id}': {e}")
            failed_count += 1

    print("\n--- Ingestion Summary ---")
    print(f"Successfully ingested sessions: {ingested_count}")
    print(f"Failed to ingest sessions: {failed_count}")
    print(f"Total sessions processed: {len(extracted_sessions)}")


if __name__ == "__main__":
    asyncio.run(main())
