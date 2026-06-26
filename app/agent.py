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

from .config import setup_env
setup_env()

from .tools import (
    list_vault_notes,
    read_note,
    update_note,
    create_vault_directory,
    move_note,
    set_vault_path,
)

ORGANIZER_INSTRUCTION = """You are an Obsidian vault organization expert.
Your goal is to intelligently organize scattered markdown (.md) files in the user's vault.

When the user asks you a question or gives a command, use the appropriate tools to fulfill their specific request (e.g. just list notes if they ask to list them).
Only proceed with the full organization process if they ask you to organize the vault or perform a broad task.

When organizing the vault, follow this process:
1. Scan the vault using `list_vault_notes` to see all available files.
   - The response includes `vault_path` (the directory that was actually scanned), `notes` (the .md files found), and `total_files` (all files including non-.md).
   - Always tell the user which `vault_path` was scanned.
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

IMPORTANT: After making tool calls, always respond to the user with a text message summarizing the results. If you are asked to list notes, list them in text and stop. If you are asked to organize, summarize your actions after finishing.
"""


class RateLimiterPlugin(BasePlugin):
    """Enforces requests-per-minute (RPM) rate limits on model requests using a token bucket."""

    def __init__(self, rpm: int = 15, burst: int = 5):
        super().__init__(name="rate_limiter_plugin")
        self.rpm = rpm
        self.capacity = burst
        self.tokens = float(burst)
        self.last_refill = time.time()
        self.lock = asyncio.Lock()

    async def before_model_callback(self, *, callback_context, llm_request) -> None:
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            # Refill rate: rpm / 60.0 tokens per second
            self.tokens = min(self.capacity, self.tokens + elapsed * (self.rpm / 60.0))
            self.last_refill = now

            if self.tokens < 1.0:
                # Calculate sleep time needed to get at least 1.0 token
                tokens_needed = 1.0 - self.tokens
                sleep_time = tokens_needed / (self.rpm / 60.0)
                await asyncio.sleep(sleep_time)
                # Refill again after sleep
                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * (self.rpm / 60.0))
                self.last_refill = now

            self.tokens -= 1.0
        return None


rate_limiter = RateLimiterPlugin(rpm=15)

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
        update_note,
        create_vault_directory,
        move_note,
        set_vault_path,
    ],
    before_model_callback=rate_limiter.before_model_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
