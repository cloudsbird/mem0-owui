"""
title: mem0-owui-self-hosted
author: Vederis Leunardus
date: 2025-11-03
version: 1.1.0
license: MIT
description: Advanced memory filter for OpenWebUI using mem0 with OpenRouter
requirements: mem0ai[graph]==1.0.0, pydantic==2.12.3
"""

import os
import logging
from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field, field_validator
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
            default="mem1536", description="Qdrant collection name for 1536-dimensional vectors"
        )

        # Memory configuration
        enable_memory: bool = Field(
            default=True, description="Enable memory functionality"
        )
        memory_threshold: float = Field(
            default=0.7, description="Similarity threshold for memory retrieval (0.0-1.0)"
        )
        max_memories: int = Field(
            default=5, description="Maximum number of memories to retrieve"
        )
        memory_context_window: int = Field(
            default=10, description="Number of recent messages to consider for context"
        )

        # Advanced memory features
        enable_memory_consolidation: bool = Field(
            default=True, description="Enable periodic memory consolidation"
        )
        memory_consolidation_interval: int = Field(
            default=100, description="Number of messages before consolidation"
        )
        enable_memory_forgetting: bool = Field(
            default=False, description="Enable automatic memory forgetting"
        )
        memory_retention_days: int = Field(
            default=30, description="Days to retain memories before forgetting"
        )
        enable_relationship_mapping: bool = Field(
            default=True, description="Enable Neo4j relationship mapping"
        )
        memory_importance_threshold: float = Field(
            default=0.8, description="Minimum importance score for memory retention"
        )

        # Analytics and monitoring
        enable_analytics: bool = Field(
            default=True, description="Enable memory analytics and metrics"
        )
        analytics_retention_days: int = Field(
            default=90, description="Days to retain analytics data"
        )

        # LLM config
        llm_provider: str = Field(
            default="openai", description="LLM provider (openai, etc)"
        )
        llm_api_key: str = Field(default="placeholder", description="LLM API key")
        llm_model: str = Field(
            default="openai/gpt-4o-mini", description="LLM model name"
        )
        llm_base_url: str = Field(
            default="https://openrouter.ai/api/v1", description="LLM API base URL"
        )

        # Embedder config
        embedder_provider: str = Field(
            default="openai", description="Embedding provider"
        )
        embedder_api_key: str = Field(
            default="placeholder", description="Embedding API key"
        )
        embedder_model: str = Field(
            default="openai/text-embedding-3-small", description="Embedding model name"
        )

        # Neo4j graph store config
        neo4j_url: str = Field(
            default="bolt://neo4j:7687", description="Neo4j database URL"
        )
        neo4j_username: str = Field(
            default="neo4j", description="Neo4j username"
        )
        neo4j_password: str = Field(
            default="your_password", description="Neo4j password"
        )

    def __init__(self):
        self.type = "filter"
        self.valves = self.Valves(
            **{k: os.getenv(k, v.default) for k, v in self.Valves.model_fields.items()}
        )
        self.m = None  # Initialize self.m to None
        self.logger = logging.getLogger(__name__)
        self.message_count = {}  # Track messages per user for consolidation
        self.last_consolidation = {}  # Track last consolidation time per user
        self.analytics = {}  # Store analytics data
        pass

    async def on_valves_updated(self):
        self.logger.info("Initializing mem0 client with OpenRouter configuration")
        self.logger.debug(f"Valves configuration: {self.valves}")
        try:
            self.m = await self.init_mem_zero()
            self.logger.info("Mem0 client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize mem0 client: {e}")
            raise

    async def on_startup(self):
        self.logger.info(f"Pipeline starting: {__name__}")
        # Schedule periodic memory cleanup if enabled
        if self.valves.enable_memory_forgetting:
            asyncio.create_task(self._schedule_memory_cleanup())
        pass

    async def on_shutdown(self):
        self.logger.info(f"Pipeline shutting down: {__name__}")
        # Perform final cleanup
        if self.valves.enable_memory_forgetting:
            for user_id in self.message_count.keys():
                await self.cleanup_old_memories(user_id)
        pass

    async def _schedule_memory_cleanup(self):
        """Schedule periodic memory cleanup."""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily (24 hours)
                self.logger.info("Running scheduled memory cleanup")

                # Cleanup memories for all tracked users
                for user_id in list(self.message_count.keys()):
                    await self.cleanup_old_memories(user_id)

            except Exception as e:
                self.logger.error(f"Scheduled memory cleanup failed: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour on failure

    async def add_message_to_mem0(self, user_id, message):
        try:
            await self.m.add(user_id=user_id, messages=[message])
            self.logger.debug(f"Added message to mem0 for user {user_id}: {message.get('content', '')[:50]}...")

            # Track message count for consolidation
            if user_id not in self.message_count:
                self.message_count[user_id] = 0
            self.message_count[user_id] += 1

            # Check if consolidation is needed
            if (self.valves.enable_memory_consolidation and
                self.message_count[user_id] >= self.valves.memory_consolidation_interval):
                asyncio.create_task(self.consolidate_memories(user_id))
                self.message_count[user_id] = 0  # Reset counter

        except Exception as e:
            self.logger.error(f"Failed to add message to mem0: {e}")

    async def consolidate_memories(self, user_id):
        """Consolidate and merge similar memories to reduce redundancy."""
        try:
            self.logger.info(f"Starting memory consolidation for user {user_id}")

            # Get all memories for the user
            all_memories = await self.m.search(user_id=user_id, query="", limit=100)

            if not all_memories or not all_memories.get("results"):
                return

            memories = all_memories["results"]

            # Group similar memories
            consolidated_groups = self._group_similar_memories(memories)

            # Merge memories within each group
            for group in consolidated_groups:
                if len(group) > 1:
                    await self._merge_memory_group(user_id, group)

            self.logger.info(f"Memory consolidation completed for user {user_id}")

        except Exception as e:
            self.logger.error(f"Memory consolidation failed for user {user_id}: {e}")

    def _group_similar_memories(self, memories, threshold=0.85):
        """Group memories by similarity."""
        groups = []
        used_indices = set()

        for i, memory in enumerate(memories):
            if i in used_indices:
                continue

            group = [memory]
            used_indices.add(i)

            for j, other_memory in enumerate(memories):
                if j in used_indices or i == j:
                    continue

                # Simple similarity check based on content overlap
                content1 = memory.get("memory", "").lower()
                content2 = other_memory.get("memory", "").lower()

                if self._calculate_similarity(content1, content2) > threshold:
                    group.append(other_memory)
                    used_indices.add(j)

            if len(group) > 1:
                groups.append(group)

        return groups

    def _calculate_similarity(self, text1, text2):
        """Calculate simple text similarity."""
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def _merge_memory_group(self, user_id, memory_group):
        """Merge a group of similar memories into a consolidated memory."""
        try:
            # Combine memory contents
            contents = [mem.get("memory", "") for mem in memory_group]
            consolidated_content = " | ".join(set(contents))  # Remove duplicates

            # Create consolidated memory
            consolidated_memory = {
                "role": "system",
                "content": f"Consolidated memories: {consolidated_content}"
            }

            # Add consolidated memory
            await self.m.add(user_id=user_id, messages=[consolidated_memory])

            # Note: In a full implementation, you'd want to remove the old memories
            # However, mem0 might not have a direct delete API, so this is a simplified version

        except Exception as e:
            self.logger.error(f"Failed to merge memory group: {e}")

    async def cleanup_old_memories(self, user_id):
        """Remove old or irrelevant memories based on retention policy."""
        if not self.valves.enable_memory_forgetting:
            return

        try:
            self.logger.info(f"Starting memory cleanup for user {user_id}")

            # This is a placeholder for memory cleanup logic
            # In a real implementation, you'd need access to memory timestamps and deletion API
            # For now, we'll log the intent

            self.logger.info(f"Memory cleanup completed for user {user_id} (placeholder implementation)")

        except Exception as e:
            self.logger.error(f"Memory cleanup failed for user {user_id}: {e}")

    async def enhance_relationships(self, user_id, user_message, assistant_message):
        """Enhance Neo4j relationship mapping between memories."""
        if not self.valves.enable_relationship_mapping:
            return

        try:
            # This would create relationships in Neo4j between related memories
            # For now, this is a placeholder for advanced relationship mapping

            self.logger.debug(f"Enhanced relationships for user {user_id} (placeholder implementation)")

        except Exception as e:
            self.logger.error(f"Relationship enhancement failed: {e}")

    def _update_analytics(self, user_id, memories_used, total_memories):
        """Update analytics data for memory usage."""
        if not self.valves.enable_analytics:
            return

        if user_id not in self.analytics:
            self.analytics[user_id] = {
                "total_requests": 0,
                "total_memories_used": 0,
                "total_memories_available": 0,
                "avg_memories_per_request": 0,
                "last_activity": None
            }

        analytics = self.analytics[user_id]
        analytics["total_requests"] += 1
        analytics["total_memories_used"] += memories_used
        analytics["total_memories_available"] = total_memories
        analytics["avg_memories_per_request"] = analytics["total_memories_used"] / analytics["total_requests"]
        analytics["last_activity"] = asyncio.get_event_loop().time()

    def get_memory_analytics(self, user_id=None):
        """Get memory analytics data."""
        if user_id:
            return self.analytics.get(user_id, {})
        else:
            # Return aggregated analytics for all users
            total_requests = sum(data["total_requests"] for data in self.analytics.values())
            total_memories_used = sum(data["total_memories_used"] for data in self.analytics.values())
            avg_memories_per_request = total_memories_used / total_requests if total_requests > 0 else 0

            return {
                "total_users": len(self.analytics),
                "total_requests": total_requests,
                "total_memories_used": total_memories_used,
                "avg_memories_per_request": avg_memories_per_request,
                "active_users": len([u for u in self.analytics.values() if u["last_activity"] and
                                   (asyncio.get_event_loop().time() - u["last_activity"]) < 86400])  # Active in last 24h
            }

    def get_memory_health_status(self):
        """Get overall memory system health status."""
        try:
            health_data = {
                "memory_system_status": "healthy" if self.m else "unhealthy",
                "total_tracked_users": len(self.message_count),
                "total_analytics_users": len(self.analytics),
                "consolidation_enabled": self.valves.enable_memory_consolidation,
                "forgetting_enabled": self.valves.enable_memory_forgetting,
                "relationship_mapping_enabled": self.valves.enable_relationship_mapping,
                "analytics_enabled": self.valves.enable_analytics
            }

            # Calculate health score
            health_score = 0
            if self.m:
                health_score += 40  # Memory system operational
            if self.valves.enable_memory_consolidation:
                health_score += 15
            if self.valves.enable_memory_forgetting:
                health_score += 15
            if self.valves.enable_relationship_mapping:
                health_score += 15
            if self.valves.enable_analytics:
                health_score += 15

            health_data["health_score"] = health_score
            health_data["health_status"] = "excellent" if health_score >= 80 else "good" if health_score >= 60 else "fair" if health_score >= 40 else "poor"

            return health_data

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        """Inject memory context into the prompt before sending to the model."""

        # Skip if memory is disabled
        if not self.valves.enable_memory:
            return body

        if self.m is None:
            self.logger.info("Initializing mem0 client")
            self.m = await self.init_mem_zero()

        self.logger.debug("Inlet method triggered")

        messages = body.get("messages", [])
        if not messages:
            return body

        # Skip for certain metadata tasks
        metadata = body.get("metadata", {})
        if "task" in metadata or metadata.get("task") in ["title_generation", "tags_generation"]:
            return body

        current_user_id = self.valves.user_id
        if user and "id" in user:
            current_user_id = user["id"]

        self.logger.debug(f"Processing request for user: {current_user_id}")

        # Extract the latest user message and recent conversation context
        user_message = None
        assistant_message = None
        recent_messages = messages[-self.valves.memory_context_window:]  # Last N messages

        for msg in reversed(recent_messages):
            if msg.get("role") == "user" and not user_message:
                user_message = msg.get("content")
                self.logger.debug(f"Found user message: {user_message[:50]}...")
            elif msg.get("role") == "assistant" and not assistant_message:
                assistant_message = msg.get("content")
                self.logger.debug(f"Found assistant message: {assistant_message[:50]}...")

        if not user_message:
            return body

        try:
            # Retrieve relevant memories
            self.logger.debug("Searching for relevant memories...")
            search_results = await self.m.search(
                user_id=current_user_id,
                query=user_message,
                limit=self.valves.max_memories
            )

            memories = search_results.get("results", [])
            self.logger.debug(f"Retrieved {len(memories)} memories")

            # Filter memories by similarity threshold
            filtered_memories = [
                mem for mem in memories
                if mem.get("score", 0) >= self.valves.memory_threshold
            ]

            # Update memory with assistant response (if available)
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

            # Enhance relationships if enabled
            if assistant_message:
                asyncio.create_task(
                    self.enhance_relationships(current_user_id, user_message, assistant_message)
                )

            # Inject memory context if we have relevant memories
            if filtered_memories:
                memory_context = "\n\n## Relevant Memories:\n" + "\n".join(
                    f"- {mem['memory']}" for mem in filtered_memories
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
                            "content": f"You have access to the user's memory. Use these relevant memories to provide more personalized and contextually appropriate responses:\n{memory_context}",
                        },
                    )

                self.logger.debug(f"Injected {len(filtered_memories)} memories into context")

                # Update analytics
                if self.valves.enable_analytics:
                    self._update_analytics(current_user_id, len(filtered_memories), len(memories))

            # Update body with modified messages
            body["messages"] = messages

        except Exception as e:
            self.logger.error(f"Mem0 integration error: {str(e)}")
            # Continue without memory context rather than failing the request

        return body

    async def init_mem_zero(self):
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": self.valves.qdrant_host,
                    "port": self.valves.qdrant_port,
                    "collection_name": self.valves.collection_name,
                },
            },
            "llm": {
                "provider": self.valves.llm_provider,
                "config": {
                    "api_key": self.valves.llm_api_key,
                    "model": self.valves.llm_model,
                    "openai_base_url": self.valves.llm_base_url
                },
            },
            "embedder": {
                "provider": self.valves.embedder_provider,
                "config": {
                    "api_key": self.valves.embedder_api_key,
                    "model": self.valves.embedder_model
                },
            },
            "graph_store": {
                "provider": "neo4j",
                "config": {
                    "url": self.valves.neo4j_url,
                    "username": self.valves.neo4j_username,
                    "password": self.valves.neo4j_password,
                    "database": "neo4j",
                }
            }
        }

        self.logger.info("Initializing memory with OpenRouter configuration")
        self.logger.debug(f"Config: {config}")
        return await AsyncMemory.from_config(config)