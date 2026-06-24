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
)

ORGANIZER_INSTRUCTION = """You are an Obsidian vault organization expert.
Your goal is to intelligently organize scattered markdown (.md) files in the user's vault.

To achieve this:
1. Scan the vault using `list_vault_notes` to see all available files.
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
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
    plugins=[RateLimiterPlugin(rpm=15)],
)

