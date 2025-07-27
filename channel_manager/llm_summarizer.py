import logging
import os
from typing import Dict
import time

import openai
from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMSummarizer:
    def __init__(self, llm_config: Dict, retry_attempts: int = 3, retry_delay_seconds: int = 5):
        self.api_key = os.getenv(llm_config.get('llm_api_key_env', 'LLM_PROVIDER_API_KEY'))
        self.base_url = llm_config.get('llm_base_url', 'https://api.openai.com/v1')
        self.model = llm_config.get('llm_model', 'gpt-4o-mini')
        self.prompt_template = llm_config.get('llm_prompt_template', 
            "Summarize the following YouTube video content. Focus on main topics, key points, and important takeaways.\n\nContent: {content}"
        )
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = retry_delay_seconds

        if not self.api_key:
            logger.error("LLM API key not found. Please set the appropriate environment variable.")
            raise ValueError("LLM API key is required.")

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
                    max_tokens=500,  # Limit summary length
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.retry_attempts} failed to generate summary with LLM: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay_seconds)
        logger.error(f"Failed to generate summary after {self.retry_attempts} attempts.")
        return "Summary unavailable due to an error."