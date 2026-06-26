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
import os

import dotenv
import google.auth
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

from app.config import setup_env
setup_env()

setup_telemetry()
import logging

try:
    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
    has_gcp_credentials = True
except Exception:
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    logging.basicConfig(level=logging.INFO)
    py_logger = logging.getLogger(__name__)

    # Provide a mock for structured logging used in endpoints
    class MockLogger:
        def __init__(self, logger_obj):
            self.logger_obj = logger_obj

        def log_struct(self, info: dict, severity: str = "INFO"):
            self.logger_obj.info(f"[{severity}] {info}")

    logger = MockLogger(py_logger)
    has_gcp_credentials = False

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

# Disable cloud telemetry if we are using Google AI Studio key or have no GCP credentials
otel_to_cloud = (
    has_gcp_credentials
    and os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True"
)
if os.environ.get("GOOGLE_API_KEY"):
    otel_to_cloud = False

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=otel_to_cloud,
)
app.title = "obsidian-organizer"
app.description = "API for interacting with the Agent obsidian-organizer"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
