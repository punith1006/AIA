from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from google.genai import types as genai_types
from google.adk.models import Gemini
import os
from dataclasses import dataclass

import google.auth

# To use AI Studio credentials:
# 1. Create a .env file in the /app directory with:
#    GOOGLE_GENAI_USE_VERTEXAI=FALSE
#    GOOGLE_API_KEY=PASTE_YOUR_ACTUAL_API_KEY_HERE
# 2. This will override the default Vertex AI configuration
# _, project_id = google.auth.default()
# os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
# os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
# os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")


@dataclass
class ResearchConfiguration:
    """Configuration for research-related models and parameters.

    Attributes:
        critic_model (str): Model for evaluation tasks.
        worker_model (str): Model for working/generation tasks.
        max_search_iterations (int): Maximum search iterations allowed.
    """

    # critic_model: str = "gemini-2.5-flash"
    # worker_model: str = "gemini-2.5-flash-lite"
    critic_model = LiteLlm(model="openai/gpt-5-mini",num_retries=3,fallbacks=["openai/gpt-5","openai/gpt-5-mini","openai/gpt-5"])
    worker_model = LiteLlm(model="openai/gpt-5-nano",num_retries=3,fallbacks=["openai/gpt-5-mini","openai/gpt-5-nano","openai/gpt-5"])
    search_model = Gemini(
            model="gemini-2.5-flash",
            retry_options=genai_types.HttpRetryOptions(
            initial_delay=5,
            attempts=5
            )
        )
    max_search_iterations: int = 0


config = ResearchConfiguration()