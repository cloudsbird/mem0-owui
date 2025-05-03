# mem0-owui

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A memory filter integration for OpenWebUI using mem0 to persist and retrieve conversation context.

## Features
- Automatic memory context injection into prompts
- User-specific memory management
- LLM-generated memory summarization
- Seamless integration with OpenWebUI dashboard

## Installations

1. Make sure you have pipelines installed
2. You can Download the `mem0-owui.py`
3. Upload under `Settings > Admin Settings > Pipelines > Select the "mem0-oqui.py" > Upload`
4. Put your API Key from mem0.
5. You are good to go

## Usage
1. Set your mem0 API key in OpenWebUI dashboard under:
   `Settings > Admin Settings > Pipelines > mem0-owui > API Key`

2. The filter will automatically:
   - Retrieve relevant memories before LLM processing
   - Store new memories after LLM responses
   - Handle user-specific context isolation

## Configuration
Configure through OpenWebUI dashboard:
- `api_key`: Your mem0 API key (required)
- `user_id`: Default user ID for memory storage
- `pipelines`: Pipeline IDs to apply the filter to
- `priority`: Filter execution order

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License
MIT License - see LICENSE file
