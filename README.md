# Obsidian Organizer Agent

An AI-powered ReAct agent designed to automatically organize your Obsidian markdown vaults. It analyzes notes, adds structured tags, creates folder hierarchies, and connects related notes via wikilinks.

## Architecture

This project is built using the **Google Agent Development Kit (ADK)** and managed via the `agents-cli`. 

### Key Components

- **Agent Framework**: Uses ADK's `Agent` and `App` classes to implement a ReAct loop.
- **LLM**: Powered by Gemini (configured to use `gemma-4-26b-a4b-it` by default).
- **Tools**: The agent interacts with the file system using specialized tools:
  - `list_vault_notes`, `read_note`, `update_note`, `create_vault_directory`, `move_note`, `set_vault_path`
- **Rate Limiting**: Includes a custom `RateLimiterPlugin` that uses a token bucket algorithm to enforce requests-per-minute limits.

```
obsidian-organizer/
├── app/
│   ├── agent.py               # Main agent logic and initialization
│   ├── config.py              # Environment configuration
│   └── tools.py               # File system interaction tools
├── tests/                     # Unit and integration tests
├── pyproject.toml             # Project dependencies (managed by uv)
└── agents-cli-manifest.yaml   # CLI configuration
```

## Setup & Running on Another System

### Prerequisites

1. **Python Package Manager (`uv`)**: We use `uv` for lightning-fast dependency management.
   - Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or follow [official docs](https://docs.astral.sh/uv/getting-started/installation/))
2. **Google Agents CLI**:
   - Install globally: `uv tool install google-agents-cli`
3. **Google Cloud Auth** (Optional, if using GCP models): 
   - Install the `gcloud` CLI and run `gcloud auth application-default login`.

### Installation

1. **Clone the repository**:
   ```bash
   git clone <GITHUB_URL_PLACEHOLDER>
   cd obsidian-organizer
   ```

2. **Setup the environment**:
   Install all required dependencies:
   ```bash
   agents-cli install
   ```
   *(This creates a `.venv` using `uv` and installs packages from `pyproject.toml`)*

3. **Configure Environment Variables**:
   Create a `.env` file or set environment variables directly if needed (e.g., API keys, default vault paths).

### Running the Agent

You can test and interact with the agent locally using the playground:

```bash
agents-cli playground
```

This will launch a local web server (typically on `http://127.0.0.1:8080`) where you can interact with the agent in a chat UI.

### Testing

Run the test suite using pytest via uv:

```bash
uv run pytest tests/unit tests/integration
```
