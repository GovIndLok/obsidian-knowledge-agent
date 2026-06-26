import os
import google.auth
import dotenv

def setup_env() -> str:
    """Sets up the environment configuration. Returns the project ID."""
    if os.environ.get("_ENV_SETUP_COMPLETE"):
        return os.environ.get("GOOGLE_CLOUD_PROJECT", "mock-project-id")
        
    # Load environment variables from .env file
    dotenv.load_dotenv()

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
