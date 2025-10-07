import os
import time
from typing import Dict, Optional, Tuple
from pathlib import Path

import openai
from openai import OpenAI
from ..utils.retry import api_retry
from ..utils.logging_config import LoggerFactory
# Multi-model result handling will be done through database service

logger = LoggerFactory.create_logger(__name__)

class MultiModelLLMService:
    def __init__(self, llm_config: Dict):
        self.llm_config = llm_config
        
        # Check if multi-model is enabled
        multi_model_config = llm_config.get('multi_model', {})
        self.multi_model_enabled = multi_model_config.get('enabled', False)
        
        if not self.multi_model_enabled:
            raise ValueError("Multi-model is not enabled in configuration")
        
        # Initialize base configuration
        self._init_base_config(llm_config)
        
        # Initialize multi-model specific configuration
        self._init_multi_model_config(multi_model_config)
        
        # Initialize OpenAI clients
        self._init_clients()
        
        logger.info("MultiModelLLMService initialized", 
                   primary_model=self.primary_model,
                   secondary_model=self.secondary_model,
                   synthesis_model=self.synthesis_model)

    def _init_base_config(self, llm_config: Dict):
        """Initialize base LLM configuration"""
        # Get API key
        api_key_env_var = llm_config.get('llm_api_key_env', 'LLM_PROVIDER_API_KEY')
        self.api_key = os.getenv(api_key_env_var)
        if not self.api_key:
            raise ValueError(f"LLM API key not found. Set environment variable: {api_key_env_var}")

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

    def _init_multi_model_config(self, multi_model_config: Dict):
        """Initialize multi-model specific configuration"""
        self.primary_model = multi_model_config.get('primary_model', 'gpt-4o-mini')
        self.secondary_model = multi_model_config.get('secondary_model', 'anthropic/claude-3-haiku')
        self.synthesis_model = multi_model_config.get('synthesis_model', 'gpt-4o')
        
        self.fallback_strategy = multi_model_config.get('fallback_strategy', 'best_summary')
        
        # Get synthesis prompt template
        synthesis_template_path = multi_model_config.get('synthesis_prompt_template_path')
        if synthesis_template_path:
            try:
                with open(synthesis_template_path, 'r', encoding='utf-8') as f:
                    self.synthesis_template = f.read()
            except FileNotFoundError:
                raise ValueError(f"Synthesis template file not found: {synthesis_template_path}")
        else:
            self.synthesis_template = """
You are synthesizing two AI-generated summaries to create the best possible final summary.

**SUMMARY A:**
{summary_a}

**SUMMARY B:**
{summary_b}

**ORIGINAL CONTENT:**
{original_content}

Create a comprehensive final summary that combines the best insights from both summaries while maintaining accuracy and the creator's voice.
"""

    def _init_clients(self):
        """Initialize OpenAI clients"""
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @api_retry
    def _generate_single_summary(self, content: str, model: str, summary_type: str = "summary") -> tuple[str, dict]:
        """Generate a single summary using specified model
        
        Returns:
            tuple: (summary_text, usage_dict) where usage_dict contains token counts and cost
        """
        if not content:
            logger.warning("Empty content provided for summarization")
            return "No content to summarize", {}

        prompt = self.prompt_template.format(content=content)
        logger.info("Generating summary", 
                   content_length=len(content), 
                   model=model, 
                   summary_type=summary_type)

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert content analyst who creates comprehensive, detailed summaries while preserving the original author's voice and style."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        summary = response.choices[0].message.content.strip()
        
        # COST: Extract usage information and actual cost from OpenRouter response
        usage_dict = {}
        if hasattr(response, 'usage') and response.usage:
            usage_dict = {
                'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                'total_tokens': getattr(response.usage, 'total_tokens', 0),
                'cost': 0.0
            }
        
        # OpenRouter returns cost in different ways depending on the response format
        # Check multiple possible locations for cost data
        cost = 0.0
        
        # Method 1: Check usage object for cost (some OpenRouter responses)
        if hasattr(response, 'usage') and hasattr(response.usage, 'cost'):
            cost = float(getattr(response.usage, 'cost', 0.0))
        
        # Method 2: Check for x_openrouter metadata
        elif hasattr(response, 'x_openrouter') and hasattr(response.x_openrouter, 'cost'):
            cost = float(getattr(response.x_openrouter, 'cost', 0.0))
        
        # Method 3: Check response metadata/headers (raw response object)
        elif hasattr(response, '_raw_response'):
            raw = response._raw_response
            if hasattr(raw, 'headers') and 'x-openrouter-cost' in raw.headers:
                try:
                    cost = float(raw.headers['x-openrouter-cost'])
                except (ValueError, TypeError):
                    pass
        
        usage_dict['cost'] = cost
        
        logger.info("Generated summary", 
                   summary_length=len(summary), 
                   model=model,
                   summary_type=summary_type,
                   usage=usage_dict,
                   cost_usd=f"${cost:.6f}",
                   preview=summary[:200])
        
        if not summary:
            logger.warning("LLM returned empty summary", model=model)
            return f"Summary generation failed - empty response from {model}", usage_dict
        
        return summary, usage_dict

    @api_retry
    def _synthesize_summaries(self, summary_a: str, summary_b: str, original_content: str) -> tuple[str, dict]:
        """Synthesize two summaries into a final enhanced summary
        
        Returns:
            tuple: (synthesis_text, usage_dict) where usage_dict contains token counts and cost
        """
        logger.info("Synthesizing summaries", 
                   summary_a_length=len(summary_a),
                   summary_b_length=len(summary_b),
                   model=self.synthesis_model)

        # Prepare synthesis prompt
        synthesis_prompt = self.synthesis_template.format(
            summary_a=summary_a,
            summary_b=summary_b,
            original_content=original_content[:10000],  # Limit original content for synthesis
            model_a=self.primary_model,
            model_b=self.secondary_model,
            creator_context="Two Minute Papers - Dr. Károly Zsolnai-Fehér's enthusiastic, technical AI research summaries"
        )

        response = self.client.chat.completions.create(
            model=self.synthesis_model,
            messages=[
                {"role": "system", "content": "You are an expert synthesis specialist who combines multiple AI summaries into the highest quality final summary possible."},
                {"role": "user", "content": synthesis_prompt}
            ],
            max_tokens=3000,  # Allow more tokens for synthesis
            temperature=0.5   # Lower temperature for more consistent synthesis
        )
        
        synthesis = response.choices[0].message.content.strip()
        
        # COST: Extract usage information and actual cost from OpenRouter response
        usage_dict = {}
        if hasattr(response, 'usage') and response.usage:
            usage_dict = {
                'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                'total_tokens': getattr(response.usage, 'total_tokens', 0),
                'cost': 0.0
            }
        
        # OpenRouter returns cost in different ways depending on the response format
        cost = 0.0
        
        # Method 1: Check usage object for cost
        if hasattr(response, 'usage') and hasattr(response.usage, 'cost'):
            cost = float(getattr(response.usage, 'cost', 0.0))
        
        # Method 2: Check for x_openrouter metadata
        elif hasattr(response, 'x_openrouter') and hasattr(response.x_openrouter, 'cost'):
            cost = float(getattr(response.x_openrouter, 'cost', 0.0))
        
        # Method 3: Check response metadata/headers
        elif hasattr(response, '_raw_response'):
            raw = response._raw_response
            if hasattr(raw, 'headers') and 'x-openrouter-cost' in raw.headers:
                try:
                    cost = float(raw.headers['x-openrouter-cost'])
                except (ValueError, TypeError):
                    pass
        
        usage_dict['cost'] = cost
        
        logger.info("Generated synthesis", 
                   synthesis_length=len(synthesis),
                   model=self.synthesis_model,
                   usage=usage_dict,
                   cost_usd=f"${cost:.6f}",
                   preview=synthesis[:200])
        
        return synthesis, usage_dict

    def summarize(self, content: str) -> str:
        """Generate multi-model enhanced summary (backward compatible)"""
        result = self.summarize_enhanced(content)
        return result.get('final_summary', '')
    
    def summarize_enhanced(self, content: str) -> dict:
        """Generate multi-model enhanced summary with detailed metadata
        
        Returns dict with:
        - final_summary: The synthesized summary text
        - cost_estimate: Total actual cost from OpenRouter (USD)
        - token_usage_json: JSON string with detailed token usage
        - All model outputs and metadata
        """
        start_time = time.time()
        
        result = {
            'final_summary': '',
            'summarization_method': 'multi_model',
            'primary_summary': '',
            'secondary_summary': '',
            'synthesis_summary': '',
            'primary_model': self.primary_model,
            'secondary_model': self.secondary_model,
            'synthesis_model': self.synthesis_model,
            'processing_time_seconds': 0.0,
            'fallback_used': False,
            'token_usage_json': '{}',
            'cost_estimate': 0.0
        }
        
        try:
            # Generate primary summary
            logger.info("Starting multi-model summarization", 
                       primary_model=self.primary_model,
                       secondary_model=self.secondary_model,
                       synthesis_model=self.synthesis_model)
            
            primary_summary, primary_usage = self._generate_single_summary(content, self.primary_model, "primary")
            result['primary_summary'] = primary_summary
            
            # Generate secondary summary
            secondary_summary, secondary_usage = self._generate_single_summary(content, self.secondary_model, "secondary")
            result['secondary_summary'] = secondary_summary
            
            # Synthesize summaries
            final_summary, synthesis_usage = self._synthesize_summaries(primary_summary, secondary_summary, content)
            result['synthesis_summary'] = final_summary
            result['final_summary'] = final_summary
            
            # COST: Aggregate actual costs from all three API calls
            total_cost = (
                primary_usage.get('cost', 0.0) +
                secondary_usage.get('cost', 0.0) +
                synthesis_usage.get('cost', 0.0)
            )
            result['cost_estimate'] = round(total_cost, 6)
            
            # Aggregate token usage for analytics
            import json
            token_usage = {
                'primary': primary_usage,
                'secondary': secondary_usage,
                'synthesis': synthesis_usage,
                'total_cost': total_cost
            }
            result['token_usage_json'] = json.dumps(token_usage)
            
            processing_time = time.time() - start_time
            result['processing_time_seconds'] = round(processing_time, 2)
            
            logger.info("Multi-model summarization completed",
                       processing_time_seconds=result['processing_time_seconds'],
                       total_cost_usd=f"${total_cost:.6f}",
                       primary_length=len(primary_summary),
                       secondary_length=len(secondary_summary),
                       final_length=len(final_summary))
            
            return result
            
        except Exception as e:
            logger.error("Multi-model summarization failed, falling back to single model",
                        error=str(e),
                        fallback_model=self.primary_model)
            
            # FALLBACK: Use single model on error
            result['fallback_used'] = True
            result['summarization_method'] = 'error_fallback'
            fallback_summary, fallback_usage = self._generate_single_summary(content, self.primary_model, "error_fallback")
            result['final_summary'] = fallback_summary
            result['primary_summary'] = fallback_summary
            result['cost_estimate'] = round(fallback_usage.get('cost', 0.0), 6)
            
            import json
            result['token_usage_json'] = json.dumps({'fallback': fallback_usage})
            result['processing_time_seconds'] = time.time() - start_time
            
            return result