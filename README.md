# mem0-owui

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A memory filter integration for OpenWebUI using mem0 to persist and retrieve conversation context. This integration enhances your LLM conversations by automatically injecting relevant historical context.

## Overview

mem0-owui provides three deployment options:

1. **Managed Version**: Simple setup using mem0's cloud service - just provide an API key
2. **Self-Hosted Version**: Complete control with your own vector database and embedding infrastructure
3. **OpenRouter Version**: Self-hosted with OpenRouter integration for both LLM and embeddings, plus Neo4j graph storage

## Features

- **Smart Context Injection**: Automatically inject relevant conversation history into prompts
- **User Isolation**: Maintain separate memory spaces for different users
- **LLM-Optimized Summarization**: Generate concise memory summaries using LLMs
- **Dashboard Integration**: Seamless integration with OpenWebUI's interface
- **Flexible Configuration**: Fine-tune behavior through environment variables
- **Asynchronous Processing**: Self-hosted version uses async operations for better performance

## Requirements

- **Managed Version**:
  - mem0ai Python package
  - pydantic 2.11.4
  - mem0 API key

- **Self-Hosted Version**:
  - mem0ai 0.1.96
  - pydantic 2.7.4
  - Qdrant vector database (can be run via Docker)
  - LLM provider (OpenAI, OpenRouter, etc.)
  - Embedding model provider

- **OpenRouter Version**:
  - mem0ai[graph]==1.0.0
  - pydantic==2.12.3
  - Qdrant vector database
  - Neo4j graph database
  - OpenRouter API key (for both LLM and embeddings)

## Installation

### Managed Version (Recommended)

1. Ensure pipelines are installed in your OpenWebUI instance
2. Download `mem0-owui-managed.py`
3. Upload to OpenWebUI via:  
   `Settings > Admin Settings > Pipelines > Upload`  
   Select the "mem0-owui-managed.py" file
4. Set your mem0 API key in the configuration section
5. Enable the pipeline and set appropriate priority

### Self-Hosted Version

1. Clone the repository:
   `git clone https://github.com/mem0ai/mem0-owui.git`
2. Configure Docker:
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   # Edit docker-compose.yml with your configuration
   ```
3. Start the service:
   `docker-compose up -d`
4. Configure OpenWebUI to use your self-hosted endpoint
5. Upload `mem0-owui-selfhosted.py` through the dashboard

### OpenRouter Version (Recommended)

1. Clone the repository:
   `git clone https://github.com/mem0ai/mem0-owui.git`
2. Configure Docker:
   ```bash
   cp docker-compose.example.yml docker-compose.yml
   # Edit docker-compose.yml with your OpenRouter API key and Neo4j password
   ```
3. Start the complete stack:
   ```bash
   docker-compose up -d
   ```
4. Access OpenWebUI at http://localhost:3000
5. The pipeline will be automatically loaded with OpenRouter integration

## Configuration

### Managed Version Parameters

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `api_key` | ✅ | - | Your mem0 API key |
| `user_id` | ❌ | "default_user" | Default user ID for memory storage |
| `pipelines` | ❌ | ["*"] | Pipeline IDs to apply the filter to |
| `priority` | ❌ | 0 | Filter execution order (lower = earlier) |

### Self-Hosted Version Parameters

#### Basic Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `user_id` | ❌ | "default_user" | Default user ID for memory storage |
| `pipelines` | ❌ | ["*"] | Pipeline IDs to apply the filter to |
| `priority` | ❌ | 0 | Filter execution order (lower = earlier) |

#### Vector Store Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `qdrant_host` | ✅ | "qdrant" | Qdrant vector database host |
| `qdrant_port` | ✅ | "6333" | Qdrant vector database port |
| `collection_name` | ✅ | "mem1536" | Qdrant collection name |

#### LLM Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `llm_provider` | ✅ | "openai" | LLM provider (openai, etc) |
| `llm_api_key` | ✅ | "placeholder" | LLM API key |
| `llm_model` | ✅ | "GPT-4.1" | LLM model name |
| `llm_base_url` | ✅ | "https://openrouter.ai/api/v1" | LLM API base URL |

#### Embedder Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `embedder_provider` | ✅ | "openai" | Embedding provider |
| `embedder_api_key` | ✅ | "placeholder" | Embedding API key |
| `embedder_model` | ✅ | "text-embedding-3-small" | Embedding model name |

### OpenRouter Version Parameters

#### Basic Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `user_id` | ❌ | "default_user" | Default user ID for memory storage |
| `pipelines` | ❌ | ["*"] | Pipeline IDs to apply the filter to |
| `priority` | ❌ | 0 | Filter execution order (lower = earlier) |
| `enable_memory` | ❌ | true | Enable/disable memory functionality |
| `memory_threshold` | ❌ | 0.7 | Similarity threshold for memory retrieval (0.0-1.0) |
| `max_memories` | ❌ | 5 | Maximum number of memories to retrieve |
| `memory_context_window` | ❌ | 10 | Number of recent messages to consider |

#### Vector Store Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `qdrant_host` | ✅ | "qdrant" | Qdrant vector database host |
| `qdrant_port` | ✅ | "6333" | Qdrant vector database port |
| `collection_name` | ✅ | "mem1536" | Qdrant collection name |

#### LLM Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `llm_provider` | ✅ | "openai" | LLM provider (openai) |
| `llm_api_key` | ✅ | "placeholder" | OpenRouter API key |
| `llm_model` | ✅ | "openai/gpt-4o-mini" | OpenRouter LLM model name |
| `llm_base_url` | ✅ | "https://openrouter.ai/api/v1" | OpenRouter API base URL |

#### Embedder Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `embedder_provider` | ✅ | "openai" | Embedding provider (openai) |
| `embedder_api_key` | ✅ | "placeholder" | OpenRouter API key |
| `embedder_model` | ✅ | "openai/text-embedding-3-small" | OpenRouter embedding model |

#### Neo4j Graph Store Configuration

| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `neo4j_url` | ✅ | "bolt://neo4j:7687" | Neo4j database URL |
| `neo4j_username` | ✅ | "neo4j" | Neo4j username |
| `neo4j_password` | ✅ | "your_password" | Neo4j password |

## How It Works

### Memory Workflow

1. **Input Processing**:  
   - When a user sends a message, the filter intercepts it before it reaches the LLM
   - The filter queries mem0 for relevant memories based on the user's message
   - These memories are injected into the system message to provide context

2. **Response Processing**:  
   - After the LLM generates a response, the user's message is stored in mem0
   - In the self-hosted version, the assistant's response is also stored
   - These memories are vectorized and stored for future retrieval

3. **Memory Retrieval**:
   - When the user sends a new message, the system searches for semantically similar memories
   - The most relevant memories are injected into the prompt
   - This allows the LLM to maintain context across multiple conversations

### Technical Implementation

- **Managed Version**: Uses `MemoryClient` from mem0 for a simple, synchronous implementation
- **Self-Hosted Version**: Uses `AsyncMemory` for asynchronous operations with more configuration options
- **OpenRouter Version**: Advanced implementation with `AsyncMemory`, Neo4j graph storage, configurable memory parameters, and comprehensive logging

## Troubleshooting

### Common Issues

1. **Memory Not Being Retrieved**:
   - Check that your API key is correct (managed version)
   - Verify vector store connection (self-hosted version)
   - Ensure user IDs are consistent across sessions

2. **Pipeline Not Running**:
   - Check pipeline priority - it may be overridden by other pipelines
   - Verify that the pipeline is enabled in OpenWebUI
   - Check OpenWebUI logs for any errors

3. **Self-Hosted Version Connection Issues**:
   - Verify Qdrant is running and accessible
   - Check that embedding service is operational
   - Ensure all required environment variables are set correctly

### Debugging

For detailed debugging:

```bash
# Check Docker logs for self-hosted version
docker logs mem0-owui-container

# Check OpenWebUI logs
# Location depends on your OpenWebUI installation
```

## Contributing

### Contribution Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes with descriptive messages
4. Push to your fork (`git push origin feature/your-feature`)
5. Open a pull request with detailed description

### Development Setup

```bash
# Clone the repository
git clone https://github.com/mem0ai/mem0-owui.git

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file

## FAQ

**Q: What's the difference between managed and self-hosted versions?**  
A: The managed version uses mem0's cloud service with a simple API key, while the self-hosted version gives you complete control over the vector database, embedding model, and LLM configuration.

**Q: How do I reset my API key?**  
A: Generate a new key in your mem0 dashboard and update the configuration.

**Q: Can I use this with multiple OpenWebUI instances?**  
A: Yes, use unique user IDs for each instance to maintain separate memory contexts.

**Q: What happens if the mem0 service is unavailable?**  
A: The filter will fail gracefully, allowing normal OpenWebUI operation without memory context.

**Q: Which version should I choose?**
A: The managed version is simplest to set up, the OpenRouter version offers the best balance of features and ease of use with Neo4j graph storage, while the basic self-hosted version provides maximum customization. Choose based on your needs for privacy, control, and features.

**Q: How can I customize the memory retrieval process?**
A: The OpenRouter version provides the most configuration options including similarity thresholds, memory limits, and context windows. The self-hosted version allows full control over vector database, embedding model, and LLM settings.

**Q: What are the benefits of the Neo4j graph store in the OpenRouter version?**
A: Neo4j enables advanced memory relationships and graph-based queries, allowing for more sophisticated memory retrieval and relationship mapping between different pieces of information.
