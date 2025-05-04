# mem0-owui

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/npm/v/mem0-owui/latest)]

A memory filter integration for OpenWebUI using mem0 to persist and retrieve conversation context.

## Getting Started
Quickly integrate memory management into your OpenWebUI instance with our two deployment options:

## Features
- **Smart Context Injection**: Automatically inject relevant conversation history into prompts
- **User Isolation**: Maintain separate memory spaces for different users
- **LLM-Optimized Summarization**: Generate concise memory summaries using LLMs
- **Dashboard Integration**: Seamless integration with OpenWebUI's interface
- **Flexible Configuration**: Fine-tune behavior through environment variables

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

## Usage
### Configuration Parameters
| Parameter | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEM0_API_KEY` | ✅ | - | Your mem0 API key |
| `DEFAULT_USER` | ❌ | "default" | Default user ID for memory storage |
| `PIPELINE_IDS` | ❌ | "*" | Pipeline IDs to apply the filter to |
| `PRIORITY` | ❌ | 50 | Filter execution order (lower = earlier) |

### Memory Workflow
1. **Input Processing**:  
   - Before LLM processing, relevant memories are retrieved from mem0
   - Memories are injected into the prompt context
2. **Response Processing**:  
   - After LLM response generation, new memories are stored
   - Memory summarization is triggered based on configuration

## Configuration Guide
### Environment Variables
```bash
# Required configuration
MEM0_API_KEY=your_api_key_here

# Optional configuration
DEFAULT_USER=system_user
PIPELINE_IDS=chat,rag
PRIORITY=40
```

## Troubleshooting
### Debugging Tips
1. Check pipeline logs in your Docker. 
2. Try adjust the python / Create Issues in Github.

## Contributing

### Contribution Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes with descriptive messages
4. Push to your fork (`git push origin feature/your-feature`)
5. Open a pull request with detailed description


## License
MIT License - see [LICENSE](LICENSE) file

## FAQ
**Q: How do I reset my API key?**  
A: Generate a new key in your mem0 dashboard and update the configuration.

**Q: Can I use this with multiple OpenWebUI instances?**  
A: Yes, use unique user IDs for each instance to maintain separate memory contexts.

**Q: What happens if the mem0 service is unavailable?**  
A: The filter will fail gracefully, allowing normal OpenWebUI operation without memory context.
