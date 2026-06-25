# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# MAINTENANCE NOTE: BaseAgentConfig Deprecation
# During execution/testing you may see warnings about `BaseAgentConfig` deprecation.
# BaseAgentConfig (used for declarative YAML agent configurations) is deprecated in ADK 2.0+.
# Future changes/additions to this agent should be declared programmatically using
# the Python ADK `Agent(...)` class directly (as done below with root_agent).
# Do not attempt to write declarative YAML schemas to load or configure this agent.

import os
import time
import asyncio
import google.auth
import dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.plugins.base_plugin import BasePlugin

# Load environment variables from .env file
dotenv.load_dotenv()

# Detect Google AI Studio (Gemini API) vs Vertex AI
if os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
else:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Disable progressive SSE streaming feature
os.environ["ADK_DISABLE_PROGRESSIVE_SSE_STREAMING"] = "true"

try:
    _, project_id = google.auth.default()
except Exception:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")

os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

from .tools import (
    list_vault_notes,
    read_note,
    write_note,
    create_vault_directory,
    move_note,
    set_vault_path,
)

ORGANIZER_INSTRUCTION = """You are an Obsidian vault organization expert.
Your goal is to intelligently organize scattered markdown (.md) files in the user's vault.

To achieve this:
1. Scan the vault using `list_vault_notes` to see all available files.
   - The response includes `vault_path` (the directory that was actually scanned), `notes` (the .md files found), and `total_files` (all files including non-.md).
   - Always tell the user which `vault_path` was scanned.
   - If there are only a few notes present (e.g., less than 10), list them in your response so the user knows what notes were found. If there are many notes, do not list them all to avoid cluttering the output, but proceed to use them.
   - Proceed with reading and organizing the notes automatically after scanning. Do not stop to wait for user confirmation or input unless you encounter a critical error.
   - If `notes` is empty but `total_files` > 0, tell the user how many files were found and that none are .md, then ask if they use a different extension.
   - If both `notes` and `total_files` are 0, tell the user the vault appears empty or the path may be wrong, and suggest using `set_vault_path` to correct it.
2. Read the content of the notes using `read_note` to understand their context.
3. Analyze the content to extract key topics and tags. Add or update the YAML frontmatter section at the top of each note with a structured `tags` list.
   Example frontmatter format:
   ---
   tags:
     - topic-a
     - topic-b
   ---
4. Detect relationships between notes and insert wikilink references (e.g. [[Note Name]]) inside notes where relevant.
5. Propose and create clean folder hierarchies using `create_vault_directory` and move notes into their corresponding topic folder using `move_note`.
6. Ensure that you never delete notes and preserve note content while applying tags/links.
7. If the user requests to point to a new vault or change the active directory, call `set_vault_path` to dynamically update the active vault path.

## Error Handling — CRITICAL
Whenever any tool returns `"status": "error"`, you MUST:
- Immediately tell the user what went wrong in plain language. Quote the `message` field from the tool response.
- If the error relates to a vault path (e.g. path not found, permission denied, not a directory), also tell the user what the current active vault path is.
- Ask the user to provide a corrected value so you can retry. Never silently stop or move on without telling the user about the error.

Example response when `set_vault_path` fails:
"I wasn't able to switch to that vault. The error was: <message from tool>. Your current active vault is still: <current_path>. Could you double-check the path and try again?"

Report your actions and final folder layout clearly to the user.
"""


class RateLimiterPlugin(BasePlugin):
    """Enforces requests-per-minute (RPM) rate limits on model requests using spacing delays."""

    def __init__(self, rpm: int = 15):
        super().__init__(name="rate_limiter_plugin")
        self.delay = 60.0 / rpm
        self.last_call_time = 0.0
        self.lock = asyncio.Lock()

    async def before_model_callback(self, *, callback_context, llm_request) -> None:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call_time
            sleep_time = self.delay - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            self.last_call_time = time.time()
        return None


root_agent = Agent(
    name="obsidian_organizer_agent",
    model=Gemini(
        model="gemma-4-26b-a4b-it",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=ORGANIZER_INSTRUCTION,
    tools=[
        list_vault_notes,
        read_note,
        write_note,
        create_vault_directory,
        move_note,
        set_vault_path,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
    plugins=[RateLimiterPlugin(rpm=15)],
)
