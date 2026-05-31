"""
Gemini client — singleton using google-genai SDK.
On GCP uses ADC automatically; locally falls back to GEMINI_API_KEY.
"""
import logging
from functools import lru_cache

import google.generativeai as genai

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_gemini_client() -> genai.GenerativeModel:
    """
    Returns a cached GenerativeModel configured with the correct auth.
    ADC is picked up automatically when GEMINI_API_KEY is empty (GCP env).
    """
    settings = get_settings()

    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
        logger.info("Gemini: using API key auth")
    else:
        # ADC — no explicit configure call needed on GCP
        logger.info("Gemini: using Application Default Credentials")

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=settings.gemini_max_output_tokens,
            temperature=settings.gemini_temperature,
        ),
    )
    return model
