import logging
import os
from typing import Dict
import time
from pathlib import Path

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, llm_config: Dict, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        # Get API key
        api_key_env_var = llm_config.get('llm_api_key_env', 'LLM_PROVIDER_API_KEY')
        self.api_key = os.getenv(api_key_env_var)
        if not self.api_key:
            raise ValueError(f"LLM API key not found. Set environment variable: {api_key_env_var}")

        # Get model
        llm_model_env_var = llm_config.get('llm_model_env')
        if llm_model_env_var:
            self.model = os.getenv(llm_model_env_var)
            if not self.model:
                raise ValueError(f"LLM model not found. Set environment variable: {llm_model_env_var}")
        else:
            self.model = llm_config.get('llm_model', 'gpt-4o-mini')

        # Get base URL
        llm_base_url_env_var = llm_config.get('llm_base_url_env')
        if llm_base_url_env_var:
            self.base_url = os.getenv(llm_base_url_env_var)
            if not self.base_url:
                raise ValueError(f"LLM base URL not found. Set environment variable: {llm_base_url_env_var}")
        else:
            self.base_url = llm_config.get('llm_base_url', 'https://openrouter.ai/api/v1')

        # Get prompt template
        llm_prompt_template_path = llm_config.get('llm_prompt_template_path')
        if llm_prompt_template_path:
            try:
                with open(llm_prompt_template_path, 'r', encoding='utf-8') as f:
                    self.prompt_template = f.read()
            except FileNotFoundError:
                raise ValueError(f"LLM prompt template file not found: {llm_prompt_template_path}")
        else:
            self.prompt_template = llm_config.get('llm_prompt_template', 
                "Summarize the following YouTube video content. Focus on main topics, key points, and important takeaways.\n\nContent: {content}"
            )

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def summarize(self, content: str) -> str:
        """Generate summary of video content"""
        if not content:
            return ""

        prompt = self.prompt_template.format(content=content)

        for attempt in range(self.retry_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a concise summarization assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                summary = response.choices[0].message.content.strip()
                logger.info(f"Generated summary: {summary[:100]}...")
                return summary
                
            except Exception as e:
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.error(f"Failed to generate summary after {self.retry_attempts} attempts")
                    raise

