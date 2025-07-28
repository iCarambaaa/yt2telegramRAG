import logging
import os
from typing import Dict
import time
from pathlib import Path
import asyncio # Added this import

import openai
from openai import OpenAI

from .exceptions import LLMError, ConfigurationError

logger = logging.getLogger(__name__)

class LLMSummarizer:
    def __init__(self, llm_config: Dict, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        # Determine API Key
        api_key_env_var = llm_config.get('llm_api_key_env', 'LLM_PROVIDER_API_KEY')
        self.api_key = os.getenv(api_key_env_var)
        if not self.api_key:
            raise ConfigurationError(f"LLM API key not found. Please set the environment variable: {api_key_env_var}")

        # Determine LLM Model with layered priority
        llm_model_env_var = llm_config.get('llm_model_env')
        if llm_model_env_var:
            self.model = os.getenv(llm_model_env_var)
            if not self.model:
                raise ConfigurationError(f"LLM model not found. Please set the environment variable: {llm_model_env_var}")
        else:
            self.model = llm_config.get('llm_model', 'gpt-4o-mini')

        # Determine LLM Base URL with layered priority
        llm_base_url_env_var = llm_config.get('llm_base_url_env')
        if llm_base_url_env_var:
            self.base_url = os.getenv(llm_base_url_env_var)
            if not self.base_url:
                raise ConfigurationError(f"LLM base URL not found. Please set the environment variable: {llm_base_url_env_var}")
        else:
            self.base_url = llm_config.get('llm_base_url', 'https://openrouter.ai/api/v1') # Updated default base URL

        # Determine Prompt Template from file or default
        llm_prompt_template_path = llm_config.get('llm_prompt_template_path')
        if llm_prompt_template_path:
            try:
                with open(llm_prompt_template_path, 'r', encoding='utf-8') as f:
                    self.prompt_template = f.read()
            except FileNotFoundError:
                raise ConfigurationError(f"LLM prompt template file not found: {llm_prompt_template_path}")
            except Exception as e:
                raise ConfigurationError(f"Error reading LLM prompt template file {llm_prompt_template_path}: {e}")
        else:
            self.prompt_template = llm_config.get('llm_prompt_template', 
                "Summarize the following YouTube video content. Focus on main topics, key points, and important takeaways.\n\nContent: {content}"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    async def summarize(self, content: str) -> str:
        if not content:
            return ""

        prompt = self.prompt_template.format(content=content)

        for attempt in range(self.retry_attempts):
            try:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a concise summarization assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500, # Limit summary length
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to generate summary with LLM: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
        logger.error(f"Failed to generate summary after {self.retry_attempts} attempts.")
        raise LLMError(f"Failed to generate summary after {self.retry_attempts} attempts.")