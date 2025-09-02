import os
import time
import json
from typing import Dict, Optional, Tuple
from pathlib import Path

import openai
from openai import OpenAI
from ..utils.retry import api_retry
from ..utils.logging_config import LoggerFactory
# Multi-model result handling will be done through database service

logger = LoggerFactory.create_logger(__name__)

class MultiModelLLMService:
    def __init__(self, llm_config: Dict, channel_name: Optional[str] = None):
        self.llm_config = llm_config
        self.channel_name = channel_name
        
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
                   synthesis_model=self.synthesis_model,
                   channel_name=self.channel_name)

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
        
        self.cost_threshold_tokens = multi_model_config.get('cost_threshold_tokens', 50000)
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

    def _get_creator_context(self) -> str:
        """Get creator context based on channel name"""
        if not self.channel_name:
            return "Generic content creator with engaging, informative style"
        
        channel_lower = self.channel_name.lower()
        
        if "twominutepapers" in channel_lower or "two minute papers" in channel_lower:
            return "Two Minute Papers - Dr. Károly Zsolnai-Fehér's enthusiastic, technical AI research summaries"
        elif "david" in channel_lower and "ondrej" in channel_lower:
            return "David Ondrej - Raw, unedited, documentary-like tech tutorials with entrepreneurial mindset"
        elif "isaac" in channel_lower and "arthur" in channel_lower:
            return "Isaac Arthur - Grand cosmic storytelling about space technology and megastructures"
        elif "robyn" in channel_lower:
            return "RobynHD - Sharp, no-nonsense crypto market analysis with insider perspective"
        elif "ivan" in channel_lower and "yakovina" in channel_lower:
            return "Ivan Yakovina - Geopolitical analysis with insider perspective and strategic insights"
        else:
            return f"{self.channel_name} - Engaging content creator with unique voice and perspective"

    def _calculate_cost_estimate(self, usage_data: dict) -> float:
        """Calculate estimated cost based on token usage and model pricing"""
        # Basic cost estimation - these are rough estimates and should be updated with actual pricing
        model_costs = {
            # OpenAI models (per 1K tokens)
            'gpt-4o': {'input': 0.0025, 'output': 0.01},
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
            
            # Anthropic models (per 1K tokens)
            'anthropic/claude-3-opus': {'input': 0.015, 'output': 0.075},
            'anthropic/claude-3-sonnet': {'input': 0.003, 'output': 0.015},
            'anthropic/claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
            
            # Default fallback pricing
            'default': {'input': 0.001, 'output': 0.002}
        }
        
        total_cost = 0.0
        
        for model_type, usage_info in usage_data.items():
            if not usage_info or 'total_tokens' not in usage_info:
                continue
                
            model_name = getattr(self, f"{model_type}_model", "default")
            pricing = model_costs.get(model_name, model_costs['default'])
            
            # Use prompt/completion tokens if available, otherwise estimate 70/30 split
            if 'prompt_tokens' in usage_info and 'completion_tokens' in usage_info:
                input_tokens = usage_info['prompt_tokens']
                output_tokens = usage_info['completion_tokens']
            else:
                total_tokens = usage_info['total_tokens']
                input_tokens = int(total_tokens * 0.7)  # Estimate 70% input
                output_tokens = int(total_tokens * 0.3)  # Estimate 30% output
            
            # Calculate cost (pricing is per 1K tokens)
            input_cost = (input_tokens / 1000) * pricing['input']
            output_cost = (output_tokens / 1000) * pricing['output']
            model_cost = input_cost + output_cost
            
            total_cost += model_cost
            
            logger.debug("Cost calculation", 
                        model=model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model_cost=round(model_cost, 6))
        
        return round(total_cost, 6)

    @api_retry
    def _generate_single_summary(self, content: str, model: str, summary_type: str = "summary") -> tuple[str, dict]:
        """Generate a single summary using specified model"""
        if not content:
            logger.warning("Empty content provided for summarization")
            return "No content to summarize", {}

        # Truncate content if too long
        max_content_chars = 50000
        if len(content) > max_content_chars:
            logger.info("Content too long, truncating", 
                       content_length=len(content), 
                       max_chars=max_content_chars,
                       model=model)
            content = content[:max_content_chars] + "...\n\n[Content truncated due to length]"

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
        
        # Extract usage information
        usage_info = {}
        if hasattr(response, 'usage') and response.usage:
            usage_info = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        
        logger.info("Generated summary", 
                   summary_length=len(summary), 
                   model=model,
                   summary_type=summary_type,
                   usage_info=usage_info,
                   preview=summary[:200])
        
        if not summary:
            logger.warning("LLM returned empty summary", model=model)
            return f"Summary generation failed - empty response from {model}", usage_info
        
        return summary, usage_info

    @api_retry
    def _synthesize_summaries(self, summary_a: str, summary_b: str, original_content: str) -> tuple[str, dict]:
        """Synthesize two summaries into a final enhanced summary"""
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
            creator_context=self._get_creator_context()
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
        
        # Extract usage information
        usage_info = {}
        if hasattr(response, 'usage') and response.usage:
            usage_info = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        
        logger.info("Generated synthesis", 
                   synthesis_length=len(synthesis),
                   model=self.synthesis_model,
                   usage_info=usage_info,
                   preview=synthesis[:200])
        
        return synthesis, usage_info

    def summarize(self, content: str) -> str:
        """Generate multi-model enhanced summary (backward compatible)"""
        result = self.summarize_enhanced(content)
        return result.get('final_summary', '')
    
    def summarize_enhanced(self, content: str) -> dict:
        """Generate multi-model enhanced summary with detailed metadata"""
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
        
        usage_data = {}
        
        try:
            # Estimate token count (rough approximation)
            estimated_tokens = len(content) // 4
            
            # Check if we should use fallback due to cost threshold
            if estimated_tokens > self.cost_threshold_tokens:
                logger.warning("Content exceeds cost threshold, using fallback strategy",
                             estimated_tokens=estimated_tokens,
                             threshold=self.cost_threshold_tokens,
                             fallback_strategy=self.fallback_strategy)
                
                result['fallback_used'] = True
                result['summarization_method'] = 'fallback'
                
                if self.fallback_strategy == "primary_summary":
                    fallback_summary, usage_info = self._generate_single_summary(content, self.primary_model, "fallback_primary")
                    result['final_summary'] = fallback_summary
                    result['primary_summary'] = fallback_summary
                    usage_data['primary'] = usage_info
                else:  # best_summary
                    fallback_summary, usage_info = self._generate_single_summary(content, self.synthesis_model, "fallback_best")
                    result['final_summary'] = fallback_summary
                    result['synthesis_summary'] = fallback_summary
                    usage_data['synthesis'] = usage_info
                
                # Calculate cost and finalize result
                result['cost_estimate'] = self._calculate_cost_estimate(usage_data)
                result['token_usage_json'] = json.dumps(usage_data)
                result['processing_time_seconds'] = time.time() - start_time
                return result
            
            # Generate primary summary
            logger.info("Starting multi-model summarization", 
                       primary_model=self.primary_model,
                       secondary_model=self.secondary_model,
                       synthesis_model=self.synthesis_model)
            
            primary_summary, primary_usage = self._generate_single_summary(content, self.primary_model, "primary")
            result['primary_summary'] = primary_summary
            usage_data['primary'] = primary_usage
            
            # Generate secondary summary
            secondary_summary, secondary_usage = self._generate_single_summary(content, self.secondary_model, "secondary")
            result['secondary_summary'] = secondary_summary
            usage_data['secondary'] = secondary_usage
            
            # Synthesize summaries
            final_summary, synthesis_usage = self._synthesize_summaries(primary_summary, secondary_summary, content)
            result['synthesis_summary'] = final_summary
            result['final_summary'] = final_summary
            usage_data['synthesis'] = synthesis_usage
            
            processing_time = time.time() - start_time
            result['processing_time_seconds'] = round(processing_time, 2)
            
            # Calculate total cost and store usage data
            result['cost_estimate'] = self._calculate_cost_estimate(usage_data)
            result['token_usage_json'] = json.dumps(usage_data)
            
            logger.info("Multi-model summarization completed",
                       processing_time_seconds=result['processing_time_seconds'],
                       primary_length=len(primary_summary),
                       secondary_length=len(secondary_summary),
                       final_length=len(final_summary),
                       cost_estimate=result['cost_estimate'])
            
            return result
            
        except Exception as e:
            logger.error("Multi-model summarization failed, falling back to single model",
                        error=str(e),
                        fallback_model=self.primary_model)
            
            # Fallback to single model
            result['fallback_used'] = True
            result['summarization_method'] = 'error_fallback'
            try:
                fallback_summary, fallback_usage = self._generate_single_summary(content, self.primary_model, "error_fallback")
                result['final_summary'] = fallback_summary
                result['primary_summary'] = fallback_summary
                usage_data['primary'] = fallback_usage
                result['cost_estimate'] = self._calculate_cost_estimate(usage_data)
                result['token_usage_json'] = json.dumps(usage_data)
            except Exception as fallback_error:
                logger.error("Fallback summarization also failed", error=str(fallback_error))
                result['final_summary'] = "Summary generation failed due to errors"
                result['cost_estimate'] = 0.0
                result['token_usage_json'] = '{}'
            
            result['processing_time_seconds'] = time.time() - start_time
            
            return result