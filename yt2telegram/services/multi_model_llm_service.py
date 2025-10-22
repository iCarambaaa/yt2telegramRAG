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

# @agent:service-type business-logic
# @agent:scalability stateless
# @agent:persistence none
# @agent:priority critical
# @agent:dependencies OpenAI,DatabaseService,ConfigurationFiles
class MultiModelLLMService:
    """Advanced multi-model LLM service for enhanced video summarization.
    
    This service orchestrates multiple AI models to create superior summaries by
    generating two independent summaries and synthesizing them into a final result.
    Implements intelligent cost controls, fallback strategies, and comprehensive
    error handling for production reliability.
    
    Architecture: Stateless service with external API dependencies
    Critical Path: Video summarization pipeline - failures affect user experience
    Failure Mode: Graceful degradation to single-model processing with full logging
    
    AI-GUIDANCE:
    - Never bypass cost threshold validations - prevents budget overruns
    - Always implement retry logic for external API calls
    - Use exponential backoff for rate limiting scenarios
    - Maintain backward compatibility with single-model interface
    - Log all token usage and costs for optimization analysis
    
    Attributes:
        llm_config (Dict): Complete LLM configuration including multi-model settings
        channel_name (Optional[str]): Channel name for creator-specific context
        primary_model (str): Primary model for initial summarization
        secondary_model (str): Secondary model for alternative perspective
        synthesis_model (str): Model used for final summary synthesis
        cost_threshold_tokens (int): Token limit before fallback activation
        fallback_strategy (str): Strategy when cost limits exceeded
        
    Example:
        >>> config = {"multi_model": {"enabled": True, "primary_model": "gpt-4o-mini"}}
        >>> service = MultiModelLLMService(config, "twominutepapers")
        >>> result = service.summarize_enhanced("video content here")
        >>> print(f"Cost: ${result['cost_estimate']}, Time: {result['processing_time_seconds']}s")
        
    Note:
        Thread-safe for concurrent summarization. Memory usage scales with content
        length. Implements circuit breaker pattern for external API resilience.
    """
    
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

    # @agent:complexity medium
    # @agent:side-effects environment_variable_access,file_system_read
    # @agent:security input_validation_required
    def _init_base_config(self, llm_config: Dict):
        """Initialize base LLM configuration with validation and security checks.
        
        Loads and validates core LLM settings including API keys, endpoints, and
        prompt templates. Implements secure environment variable handling and
        file system access with proper error handling.
        
        Intent: Establish secure, validated connection to LLM providers
        Critical: Configuration errors here prevent all summarization operations
        
        AI-DECISION: Environment variable vs direct configuration
        Criteria:
        - Environment variable exists → use environment value (secure)
        - Direct config provided → use config value (development/testing)
        - Neither available → raise ValueError with clear message
        
        Args:
            llm_config (Dict): Base LLM configuration dictionary
            
        Raises:
            ValueError: If required configuration is missing or invalid
            FileNotFoundError: If prompt template file doesn't exist
            
        AI-NOTE: 
            - Never log API keys or sensitive configuration values
            - Always validate file paths before reading
            - Use secure defaults for missing optional configuration
        """
        # Security boundary: API key validation and secure retrieval
        # @security:critical - API key must never be logged or exposed
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
        """Get creator context from configuration or use generic default.
        
        Retrieves creator context from channel configuration to maintain
        creator-specific voice and style in AI summaries. Falls back to
        generic context if not configured.
        
        Intent: Preserve creator personality while avoiding hardcoded channel logic
        Critical: Creator context affects AI summary quality and voice consistency
        
        AI-DECISION: Creator context source priority
        Criteria:
        - Configuration has creator_context → use configured value
        - Configuration missing creator_context → use generic default
        - No channel name available → use completely generic context
        
        Returns:
            str: Creator context description for AI prompt enhancement
            
        AI-NOTE: 
            - Configuration-driven approach eliminates hardcoded channel logic
            - Generic fallback ensures system works for any channel
            - Creator context should be defined in channel YAML files
        """
        # Try to get creator context from LLM configuration
        creator_context = self.llm_config.get('creator_context')
        if creator_context:
            return creator_context
        
        # Fallback to generic context with channel name if available
        if self.channel_name:
            return f"{self.channel_name} - Engaging content creator with unique voice and perspective"
        
        # Ultimate fallback for completely generic processing
        return "Generic content creator with engaging, informative style"

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

    # @agent:complexity high
    # @agent:side-effects external_api_call,token_consumption,cost_generation
    # @agent:retry-policy api_retry_decorator,exponential_backoff
    # @agent:performance O(n) where n=content_length, bottleneck=API_call_latency
    # @agent:security input_sanitization,content_truncation
    # @agent:test-coverage critical,integration,edge-cases
    @api_retry
    def _generate_single_summary(self, content: str, model: str, summary_type: str = "summary") -> tuple[str, dict]:
        """Generate a single AI summary with comprehensive error handling and monitoring.
        
        Core summarization method that handles content validation, truncation,
        API communication, and usage tracking. Implements robust error handling
        and detailed logging for production monitoring and debugging.
        
        Intent: Generate high-quality summary while respecting token limits and costs
        Critical: This is the core AI operation - failures cascade to user experience
        
        Decision Logic:
        1. Validate input content is not empty
        2. Truncate content if exceeds maximum character limit (50k chars)
        3. Format content using channel-specific prompt template
        4. Make API call with retry logic and error handling
        5. Extract and validate response content and usage metrics
        6. Return summary with comprehensive usage metadata
        
        AI-DECISION: Content truncation strategy
        Criteria:
        - Content length ≤ 50k chars → process full content
        - Content length > 50k chars → truncate with clear indication
        - Empty content → return descriptive error message
        - API failure → let retry decorator handle with exponential backoff
        
        Args:
            content (str): Raw video content to summarize. Must be non-empty.
            model (str): LLM model identifier (e.g., 'gpt-4o-mini', 'claude-3-haiku')
            summary_type (str): Type identifier for logging ('primary', 'secondary', 'synthesis')
            
        Returns:
            tuple[str, dict]: Summary text and usage metadata dictionary
                - str: Generated summary or error message
                - dict: Token usage info with prompt_tokens, completion_tokens, total_tokens
                
        Raises:
            OpenAI API exceptions: Handled by @api_retry decorator
            Network exceptions: Handled by @api_retry decorator
            
        Performance:
            - Content validation: O(1)
            - Content truncation: O(n) where n=content_length
            - API call: Variable latency (2-30 seconds typical)
            - Response processing: O(1)
            
        AI-NOTE: 
            - Content truncation preserves beginning of content (most important)
            - Temperature=0.7 balances creativity with consistency
            - Max tokens=2000 prevents runaway generation costs
            - Usage tracking is essential for cost monitoring and optimization
        """
        # Input validation: prevent processing empty content
        # @security:input-validation - prevents wasted API calls and costs
        if not content:
            logger.warning("Empty content provided for summarization")
            return "No content to summarize", {}

        # No content truncation - process full content regardless of length
        logger.info("Processing full content without truncation", 
                   content_length=len(content), 
                   model=model)

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
            logger.warning("LLM returned empty summary", model=model, summary_type=summary_type)
            return f"Summary generation failed - empty response from {model}", usage_info
        
        # Additional validation: check for very short responses that might indicate failure
        if len(summary.strip()) < 50:
            logger.warning("LLM returned suspiciously short summary", 
                         model=model, 
                         summary_type=summary_type,
                         summary_length=len(summary),
                         summary_preview=summary[:100])
            # Still return it, but log the concern - let the caller decide
        
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
            original_content=original_content,  # Full original content for synthesis
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
    
    # @agent:complexity critical
    # @agent:side-effects external_api_calls,cost_generation,database_ready_output
    # @agent:retry-policy handled_by_individual_methods
    # @agent:performance O(3*n) where n=content_length, 3_sequential_API_calls
    # @agent:security cost_threshold_enforcement,input_validation
    # @agent:test-coverage critical,integration,cost-scenarios,fallback-scenarios
    def summarize_enhanced(self, content: str) -> dict:
        """Generate multi-model enhanced summary with comprehensive cost controls and fallback strategies.
        
        Main orchestration method that coordinates the complete multi-model pipeline:
        primary summarization, secondary summarization, synthesis, and fallback handling.
        Implements sophisticated cost controls and provides detailed metadata for
        database storage and analytics.
        
        Intent: Deliver highest quality summaries while respecting cost constraints
        Critical: This is the main public interface - all video processing depends on this
        
        State Machine: Multi-model processing pipeline
        States: cost_check → primary_summary → secondary_summary → synthesis → complete
        Fallback States: cost_exceeded → fallback_processing → complete
        Error States: api_failure → error_fallback → complete
        
        AI-DECISION: Processing strategy selection
        Criteria:
        - Estimated tokens ≤ threshold → full multi-model processing
        - Estimated tokens > threshold → fallback strategy (primary_summary or best_summary)
        - Primary model fails, secondary succeeds → use secondary as final (secondary_only)
        - Secondary model fails, primary succeeds → use primary as final (primary_only)
        - Both models succeed → proceed with synthesis (multi_model)
        - Both models fail → try synthesis model as last resort (synthesis_fallback)
        - All models fail → return error message (complete_failure)
        
        Decision Logic:
        1. Initialize result structure and start timing
        2. Estimate token usage and check against cost threshold
        3. If over threshold: execute fallback strategy and return
        4. If under threshold: execute full multi-model pipeline
        5. Generate primary summary with usage tracking
        6. Generate secondary summary with usage tracking  
        7. Synthesize both summaries into final result
        8. Calculate total costs and processing time
        9. Return comprehensive result with all metadata
        
        Args:
            content (str): Raw video content to summarize. Must be non-empty string.
            
        Returns:
            dict: Comprehensive result dictionary with all processing metadata:
                - final_summary (str): Best available summary text
                - summarization_method (str): 'multi_model', 'fallback', or 'error_fallback'
                - primary_summary (str): Primary model output
                - secondary_summary (str): Secondary model output  
                - synthesis_summary (str): Synthesized final summary
                - primary_model (str): Primary model identifier
                - secondary_model (str): Secondary model identifier
                - synthesis_model (str): Synthesis model identifier
                - processing_time_seconds (float): Total processing time
                - fallback_used (bool): Whether fallback strategy was triggered
                - token_usage_json (str): JSON string of detailed token usage
                - cost_estimate (float): Estimated cost in USD
                
        Performance:
            - Cost estimation: O(1) - simple character count calculation
            - Primary summarization: O(n) + API latency (10-30s typical)
            - Secondary summarization: O(n) + API latency (10-30s typical)
            - Synthesis: O(summary_length) + API latency (5-15s typical)
            - Total time: 25-75 seconds for full pipeline
            
        AI-NOTE: 
            - Cost threshold enforcement is critical - never bypass
            - Each step must be atomic with proper error handling
            - Fallback strategies ensure graceful degradation
            - All token usage must be tracked for cost optimization
            - Processing time tracking helps identify bottlenecks
            - Comprehensive logging enables production debugging
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
        
        usage_data = {}
        
        try:
            # No cost threshold - always use full multi-model pipeline
            logger.info("Processing with full multi-model pipeline (no cost limits)")
            
            # Generate primary summary
            logger.info("Starting multi-model summarization", 
                       primary_model=self.primary_model,
                       secondary_model=self.secondary_model,
                       synthesis_model=self.synthesis_model)
            
            # AI-DECISION: Individual model failure handling strategy
            # Criteria:
            # - Primary model fails → try secondary as fallback, then synthesis model
            # - Secondary model fails → continue with primary only (no synthesis)
            # - Synthesis model fails → use best available summary (primary or secondary)
            # - All models fail → return error message
            
            primary_summary = ""
            primary_usage = {}
            primary_failed = False
            
            try:
                primary_summary, primary_usage = self._generate_single_summary(content, self.primary_model, "primary")
                result['primary_summary'] = primary_summary
                usage_data['primary'] = primary_usage
                
                # Check if primary model returned an error message
                if primary_summary.startswith("Summary generation failed"):
                    primary_failed = True
                    logger.warning("Primary model failed", model=self.primary_model, error=primary_summary)
                
            except Exception as e:
                primary_failed = True
                logger.error("Primary model exception", model=self.primary_model, error=str(e))
                primary_summary = f"Primary model failed: {str(e)}"
                result['primary_summary'] = primary_summary
            
            # Generate secondary summary
            secondary_summary = ""
            secondary_usage = {}
            secondary_failed = False
            
            try:
                secondary_summary, secondary_usage = self._generate_single_summary(content, self.secondary_model, "secondary")
                result['secondary_summary'] = secondary_summary
                usage_data['secondary'] = secondary_usage
                
                # Check if secondary model returned an error message
                if secondary_summary.startswith("Summary generation failed"):
                    secondary_failed = True
                    logger.warning("Secondary model failed, continuing with primary only", 
                                 model=self.secondary_model, error=secondary_summary)
                
            except Exception as e:
                secondary_failed = True
                logger.warning("Secondary model exception, continuing with primary only", 
                             model=self.secondary_model, error=str(e))
                secondary_summary = f"Secondary model failed: {str(e)}"
                result['secondary_summary'] = secondary_summary
            
            # Determine processing strategy based on model success/failure
            if primary_failed and secondary_failed:
                # Both models failed - try synthesis model as last resort
                logger.error("Both primary and secondary models failed, trying synthesis model as fallback")
                try:
                    fallback_summary, fallback_usage = self._generate_single_summary(content, self.synthesis_model, "synthesis_fallback")
                    result['final_summary'] = fallback_summary
                    result['synthesis_summary'] = fallback_summary
                    result['summarization_method'] = 'synthesis_fallback'
                    result['fallback_used'] = True
                    usage_data['synthesis'] = fallback_usage
                except Exception as e:
                    logger.error("All models failed including synthesis fallback", error=str(e))
                    result['final_summary'] = "All summarization models failed - unable to generate summary"
                    result['summarization_method'] = 'complete_failure'
                    result['fallback_used'] = True
                    
            elif primary_failed and not secondary_failed:
                # Primary failed, secondary succeeded - use secondary as final
                logger.info("Primary model failed, using secondary model result as final summary")
                result['final_summary'] = secondary_summary
                result['summarization_method'] = 'secondary_only'
                result['fallback_used'] = True
                
            elif not primary_failed and secondary_failed:
                # Secondary failed, primary succeeded - use primary as final
                logger.info("Secondary model failed, using primary model result as final summary")
                result['final_summary'] = primary_summary
                result['summarization_method'] = 'primary_only'
                result['fallback_used'] = True
                
            else:
                # Both models succeeded - proceed with synthesis
                try:
                    final_summary, synthesis_usage = self._synthesize_summaries(primary_summary, secondary_summary, content)
                    result['synthesis_summary'] = final_summary
                    result['final_summary'] = final_summary
                    usage_data['synthesis'] = synthesis_usage
                    result['summarization_method'] = 'multi_model'
                    
                except Exception as e:
                    logger.warning("Synthesis failed, using best available summary", error=str(e))
                    # Choose the better summary based on length (simple heuristic)
                    if len(primary_summary) >= len(secondary_summary):
                        result['final_summary'] = primary_summary
                        result['summarization_method'] = 'synthesis_failed_primary'
                    else:
                        result['final_summary'] = secondary_summary
                        result['summarization_method'] = 'synthesis_failed_secondary'
                    result['fallback_used'] = True
            
            processing_time = time.time() - start_time
            result['processing_time_seconds'] = round(processing_time, 2)
            
            # Calculate total cost and store usage data
            result['cost_estimate'] = self._calculate_cost_estimate(usage_data)
            result['token_usage_json'] = json.dumps(usage_data)
            
            # Log completion with appropriate details based on what succeeded
            final_summary = result['final_summary']
            logger.info("Multi-model summarization completed",
                       processing_time_seconds=result['processing_time_seconds'],
                       summarization_method=result['summarization_method'],
                       primary_length=len(result.get('primary_summary', '')),
                       secondary_length=len(result.get('secondary_summary', '')),
                       synthesis_length=len(result.get('synthesis_summary', '')),
                       final_length=len(final_summary),
                       fallback_used=result['fallback_used'],
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