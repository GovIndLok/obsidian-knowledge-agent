import os
import google.auth
import dotenv

def setup_env() -> str:
    """Sets up the environment configuration. Returns the project ID."""
    if os.environ.get("_ENV_SETUP_COMPLETE"):
        return os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")
        
    # Load environment variables from .env file
    dotenv.load_dotenv()

    # Load default vault path from config.json if it exists
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    if os.path.exists(config_path):
        import json
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                if "default_vault_path" in config_data:
                    if "OBSIDIAN_VAULT_PATH" not in os.environ:
                        os.environ["OBSIDIAN_VAULT_PATH"] = config_data["default_vault_path"]
        except Exception:
            pass


    # Detect Google AI Studio (Gemini API) vs Vertex AI
    if os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    else:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

    # Disable progressive SSE streaming feature
    os.environ["ADK_DISABLE_PROGRESSIVE_SSE_STREAMING"] = "true"

    # Skip GCP auth in tests to avoid side effects
    if "PYTEST_CURRENT_TEST" not in os.environ:
        try:
            _, project_id = google.auth.default()
        except Exception:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")
    else:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")

    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ["_ENV_SETUP_COMPLETE"] = "1"
    
    return project_id
