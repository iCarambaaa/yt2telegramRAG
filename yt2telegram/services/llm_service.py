import os
from typing import Dict
from pathlib import Path

import openai
from openai import OpenAI
from ..utils.retry import api_retry
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

# @agent:service-type business-logic
# @agent:scalability stateless
# @agent:persistence none
# @agent:priority critical
# @agent:dependencies OpenAI_API,PromptTemplates,ConfigurationFiles
class LLMService:
    """Base LLM service for single-model AI summarization with flexible provider support.
    
    Provides standardized interface for AI summarization using various LLM providers
    (OpenAI, Anthropic, OpenRouter, etc.). Handles authentication, prompt templating,
    and error recovery for reliable AI operations. Serves as base class for
    MultiModelLLMService and standalone single-model processing.
    
    Architecture: Stateless service with configurable LLM provider endpoints
    Critical Path: AI summarization - failures prevent content processing
    Failure Mode: Graceful error handling with detailed logging for debugging
    
    AI-GUIDANCE:
    - Never log API keys or sensitive authentication data
    - Preserve prompt template formatting - affects AI output quality
    - Always validate configuration before making API calls
    - Implement proper token usage tracking for cost monitoring
    - Use consistent temperature and max_tokens for reproducible results
    
    Attributes:
        api_key (str): LLM provider API key from environment
        model (str): Model identifier (e.g., 'gpt-4o-mini', 'claude-3-haiku')
        base_url (str): API endpoint URL for LLM provider
        prompt_template (str): Template for formatting summarization prompts
        client (OpenAI): Configured API client for LLM communication
        
    Example:
        >>> config = {"llm_model": "gpt-4o-mini", "llm_api_key_env": "OPENAI_API_KEY"}
        >>> service = LLMService(config)
        >>> summary = service.summarize("Video content here...")
        
    Note:
        Thread-safe for concurrent summarization. Supports OpenAI-compatible APIs.
        Automatic retry logic through @api_retry decorator.
    """
    
    def __init__(self, llm_config: Dict):

        # Security boundary: API key validation and secure retrieval
        # @security:critical - API key must never be logged or exposed
        # AI-DECISION: Environment variable vs direct configuration
        # Criteria: Environment variable → secure production deployment
        #          Direct config → development/testing only
        #          Missing key → fail fast with clear error message
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

    @api_retry
    def summarize(self, content: str) -> str:
        """Generate summary of video content"""
        if not content:
            logger.warning("Empty content provided for summarization")
            return "No content to summarize"

        # Truncate content if too long (keep within reasonable token limits)
        max_content_chars = 50000  # Roughly 12-15k tokens
        if len(content) > max_content_chars:
            logger.info("Content too long, truncating", content_length=len(content), max_chars=max_content_chars)
            content = content[:max_content_chars] + "...\n\n[Content truncated due to length]"

        prompt = self.prompt_template.format(content=content)
        logger.info("Generating summary", content_length=len(content))

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert content analyst who creates comprehensive, detailed summaries while preserving the original author's voice and style."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,  # Increased back to 2000 - issue was Markdown parsing, not length
            temperature=0.7
        )
        summary = response.choices[0].message.content.strip()
        
        # Log more details about the response
        logger.info("Generated summary", summary_length=len(summary), preview=summary[:200])
        
        if not summary:
            logger.warning("LLM returned empty summary")
            return "Summary generation failed - empty response from LLM"
        
        return summary

