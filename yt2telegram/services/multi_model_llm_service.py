"""
Multi-model LLM service for enhanced summarization through dual model approach and synthesis.
"""

import os
import time
from typing import Dict, Optional, Tuple
from pathlib import Path

from openai import OpenAI
from .llm_service import LLMService
from ..models.multi_model import MultiModelResult, TokenUsage, FallbackStrategy, ModelConfig
from ..utils.synthesis_template import SynthesisTemplateLoader, CreatorContextExtractor
from ..utils.retry import api_retry
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)


class MultiModelLLMService(LLMService):
    """
    Enhanced LLM service that uses multiple models for improved summarization quality.
    
    Pipeline:
    1. Generate two independent summaries using different models
    2. Synthesize the best final summary using a third model
    3. Fallback to single-model approach on failures
    """
    
    def __init__(self, llm_config: Dict, multi_model_config: Optional[Dict] = None):
        """
        Initialize multi-model LLM service.
        
        Args:
            llm_config: Standard LLM configuration (for backward compatibility)
            multi_model_config: Multi-model specific configuration
        """
        # Initialize parent class for backward compatibility
        super().__init__(llm_config)
        
        self.multi_model_config = multi_model_config or {}
        self.is_multi_model_enabled = self.multi_model_config.get('enabled', False)
        
        if self.is_multi_model_enabled:
            self._initialize_multi_model_configs()
            self._initialize_synthesis_template()
        
        logger.info("MultiModelLLMService initialized", 
                   multi_model_enabled=self.is_multi_model_enabled)
    
    def _initialize_multi_model_configs(self):
        """Initialize configurations for primary, secondary, and synthesis models."""
        try:
            # Primary model (defaults to parent config)
            self.primary_config = ModelConfig(
                model_name=self.multi_model_config.get('primary_model', self.model),
                api_key_env=self.multi_model_config.get('primary_api_key_env', 'LLM_PROVIDER_API_KEY'),
                base_url_env=self.multi_model_config.get('primary_base_url_env', 'BASE_URL'),
                max_tokens=self.multi_model_config.get('primary_max_tokens', 2000),
                temperature=self.multi_model_config.get('primary_temperature', 0.7)
            )
            
            # Secondary model
            self.secondary_config = ModelConfig(
                model_name=self.multi_model_config.get('secondary_model', 'claude-3-haiku-20240307'),
                api_key_env=self.multi_model_config.get('secondary_api_key_env', 'LLM_PROVIDER_API_KEY'),
                base_url_env=self.multi_model_config.get('secondary_base_url_env', 'BASE_URL'),
                max_tokens=self.multi_model_config.get('secondary_max_tokens', 2000),
                temperature=self.multi_model_config.get('secondary_temperature', 0.7)
            )
            
            # Synthesis model
            self.synthesis_config = ModelConfig(
                model_name=self.multi_model_config.get('synthesis_model', 'gpt-4o'),
                api_key_env=self.multi_model_config.get('synthesis_api_key_env', 'LLM_PROVIDER_API_KEY'),
                base_url_env=self.multi_model_config.get('synthesis_base_url_env', 'BASE_URL'),
                max_tokens=self.multi_model_config.get('synthesis_max_tokens', 2500),
                temperature=self.multi_model_config.get('synthesis_temperature', 0.7)
            )
            
            # Cost and fallback settings
            self.cost_threshold_tokens = self.multi_model_config.get('cost_threshold_tokens', 50000)
            fallback_strategy_str = self.multi_model_config.get('fallback_strategy', 'best_summary')
            self.fallback_strategy = FallbackStrategy(fallback_strategy_str)
            
            logger.info("Multi-model configurations initialized",
                       primary_model=self.primary_config.model_name,
                       secondary_model=self.secondary_config.model_name,
                       synthesis_model=self.synthesis_config.model_name,
                       cost_threshold=self.cost_threshold_tokens)
            
        except Exception as e:
            logger.error("Failed to initialize multi-model configurations", error=str(e))
            raise ValueError(f"Invalid multi-model configuration: {e}")
    
    def _initialize_synthesis_template(self):
        """Initialize synthesis template loader."""
        template_path = self.multi_model_config.get('synthesis_prompt_template_path')
        self.synthesis_loader = SynthesisTemplateLoader(template_path)
        
        # Extract creator context from existing prompt template
        if hasattr(self, 'prompt_template') and self.multi_model_config.get('llm_prompt_template_path'):
            self.creator_context = CreatorContextExtractor.extract_from_prompt_template(
                self.multi_model_config.get('llm_prompt_template_path')
            )
        else:
            self.creator_context = "Maintain the creator's distinctive voice, style, and personality from the original content."
    
    def _create_client_for_config(self, config: ModelConfig) -> OpenAI:
        """Create OpenAI client for a specific model configuration."""
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found for environment variable: {config.api_key_env}")
        
        base_url = os.getenv(config.base_url_env)
        if not base_url:
            raise ValueError(f"Base URL not found for environment variable: {config.base_url_env}")
        
        return OpenAI(api_key=api_key, base_url=base_url)
    
    @api_retry
    def _generate_summary_with_config(self, content: str, config: ModelConfig, model_name: str) -> Tuple[str, int]:
        """
        Generate summary using specific model configuration.
        
        Args:
            content: Content to summarize
            config: Model configuration to use
            model_name: Human-readable model name for logging
            
        Returns:
            Tuple of (summary, estimated_tokens)
        """
        if not content:
            logger.warning("Empty content provided for summarization", model=model_name)
            return "No content to summarize", 0
        
        # Truncate content if too long
        max_content_chars = 50000
        if len(content) > max_content_chars:
            logger.info("Content too long, truncating", 
                       model=model_name,
                       content_length=len(content), 
                       max_chars=max_content_chars)
            content = content[:max_content_chars] + "...\n\n[Content truncated due to length]"
        
        prompt = self.prompt_template.format(content=content)
        client = self._create_client_for_config(config)
        
        logger.info("Generating summary", 
                   model=model_name,
                   content_length=len(content))
        
        response = client.chat.completions.create(
            model=config.model_name,
            messages=[
                {"role": "system", "content": "You are an expert content analyst who creates comprehensive, detailed summaries while preserving the original author's voice and style."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Estimate token usage (rough approximation)
        estimated_tokens = len(prompt) // 4 + len(summary) // 4
        
        logger.info("Generated summary", 
                   model=model_name,
                   summary_length=len(summary),
                   estimated_tokens=estimated_tokens,
                   preview=summary[:200])
        
        if not summary:
            logger.warning("LLM returned empty summary", model=model_name)
            return f"Summary generation failed - empty response from {model_name}", estimated_tokens
        
        return summary, estimated_tokens
    
    @api_retry
    def synthesize_summaries(self, content: str, summary_a: str, summary_b: str) -> Tuple[str, int]:
        """
        Synthesize two summaries into a final enhanced summary.
        
        Args:
            content: Original content for conflict resolution
            summary_a: First summary to synthesize
            summary_b: Second summary to synthesize
            
        Returns:
            Tuple of (synthesized_summary, estimated_tokens)
        """
        try:
            # Format synthesis prompt
            synthesis_prompt = self.synthesis_loader.format_template(
                creator_context=self.creator_context,
                summary_a=summary_a,
                summary_b=summary_b,
                original_content=content,
                model_a=self.primary_config.model_name,
                model_b=self.secondary_config.model_name
            )
            
            client = self._create_client_for_config(self.synthesis_config)
            
            logger.info("Synthesizing summaries",
                       synthesis_model=self.synthesis_config.model_name,
                       prompt_length=len(synthesis_prompt))
            
            response = client.chat.completions.create(
                model=self.synthesis_config.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert content synthesizer who creates the highest quality summaries by combining multiple AI perspectives while preserving authentic creator voice."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                max_tokens=self.synthesis_config.max_tokens,
                temperature=self.synthesis_config.temperature
            )
            
            synthesized_summary = response.choices[0].message.content.strip()
            
            # Estimate token usage
            estimated_tokens = len(synthesis_prompt) // 4 + len(synthesized_summary) // 4
            
            logger.info("Synthesized summary generated",
                       synthesis_model=self.synthesis_config.model_name,
                       summary_length=len(synthesized_summary),
                       estimated_tokens=estimated_tokens,
                       preview=synthesized_summary[:200])
            
            if not synthesized_summary:
                logger.warning("Synthesis returned empty summary")
                return "Synthesis failed - empty response", estimated_tokens
            
            return synthesized_summary, estimated_tokens
            
        except Exception as e:
            logger.error("Synthesis failed", error=str(e))
            raise
    
    def _select_best_summary(self, summary_a: str, summary_b: str) -> str:
        """
        Select the better of two summaries based on simple heuristics.
        
        Args:
            summary_a: First summary
            summary_b: Second summary
            
        Returns:
            The better summary
        """
        # Simple heuristics for quality assessment
        def score_summary(summary: str) -> float:
            if not summary or "failed" in summary.lower():
                return 0.0
            
            score = 0.0
            
            # Length score (prefer reasonable length)
            length = len(summary)
            if 500 <= length <= 3000:
                score += 1.0
            elif length < 500:
                score += length / 500.0
            else:
                score += 3000.0 / length
            
            # Content richness (emoji, structure)
            if '**' in summary:  # Bold formatting
                score += 0.2
            if any(emoji in summary for emoji in ['🎯', '📊', '💡', '🔍', '⚡', '🚀']):
                score += 0.3
            if summary.count('\n') > 3:  # Good structure
                score += 0.2
            
            return score
        
        score_a = score_summary(summary_a)
        score_b = score_summary(summary_b)
        
        logger.info("Summary quality scores",
                   score_a=score_a,
                   score_b=score_b,
                   selected="A" if score_a >= score_b else "B")
        
        return summary_a if score_a >= score_b else summary_b
    
    def multi_model_summarize(self, content: str) -> MultiModelResult:
        """
        Perform multi-model summarization with synthesis.
        
        Args:
            content: Content to summarize
            
        Returns:
            MultiModelResult with summaries, synthesis, and metadata
        """
        start_time = time.time()
        primary_summary = ""
        secondary_summary = ""
        final_summary = ""
        primary_tokens = 0
        secondary_tokens = 0
        synthesis_tokens = 0
        fallback_used = False
        fallback_strategy = None
        error_details = None
        
        try:
            logger.info("Starting multi-model summarization pipeline")
            
            # Check cost threshold before starting
            estimated_total_tokens = len(content) // 2  # Rough estimate for all operations
            if estimated_total_tokens > self.cost_threshold_tokens:
                logger.warning("Estimated token usage exceeds threshold, falling back to single model",
                             estimated_tokens=estimated_total_tokens,
                             threshold=self.cost_threshold_tokens)
                fallback_used = True
                fallback_strategy = FallbackStrategy.SINGLE_MODEL
                final_summary = super().summarize(content)
                primary_tokens = len(content) // 4 + len(final_summary) // 4
            else:
                # Step 1: Generate primary summary
                try:
                    primary_summary, primary_tokens = self._generate_summary_with_config(
                        content, self.primary_config, "Primary"
                    )
                except Exception as e:
                    logger.error("Primary model failed", error=str(e))
                    error_details = f"Primary model error: {e}"
                
                # Step 2: Generate secondary summary
                try:
                    secondary_summary, secondary_tokens = self._generate_summary_with_config(
                        content, self.secondary_config, "Secondary"
                    )
                except Exception as e:
                    logger.error("Secondary model failed", error=str(e))
                    if not error_details:
                        error_details = f"Secondary model error: {e}"
                    else:
                        error_details += f"; Secondary model error: {e}"
                
                # Step 3: Handle partial failures
                if not primary_summary and not secondary_summary:
                    logger.error("Both primary and secondary models failed, falling back to single model")
                    fallback_used = True
                    fallback_strategy = FallbackStrategy.SINGLE_MODEL
                    final_summary = super().summarize(content)
                    primary_tokens = len(content) // 4 + len(final_summary) // 4
                elif not primary_summary:
                    logger.warning("Primary model failed, using secondary summary")
                    fallback_used = True
                    fallback_strategy = FallbackStrategy.BEST_SUMMARY
                    final_summary = secondary_summary
                elif not secondary_summary:
                    logger.warning("Secondary model failed, using primary summary")
                    fallback_used = True
                    fallback_strategy = FallbackStrategy.PRIMARY_SUMMARY
                    final_summary = primary_summary
                else:
                    # Step 4: Synthesize summaries
                    try:
                        final_summary, synthesis_tokens = self.synthesize_summaries(
                            content, primary_summary, secondary_summary
                        )
                        logger.info("Multi-model pipeline completed successfully")
                    except Exception as e:
                        logger.error("Synthesis failed, falling back to best summary", error=str(e))
                        fallback_used = True
                        fallback_strategy = self.fallback_strategy
                        
                        if fallback_strategy == FallbackStrategy.PRIMARY_SUMMARY:
                            final_summary = primary_summary
                        else:  # BEST_SUMMARY
                            final_summary = self._select_best_summary(primary_summary, secondary_summary)
                        
                        if not error_details:
                            error_details = f"Synthesis error: {e}"
                        else:
                            error_details += f"; Synthesis error: {e}"
            
            # Calculate final metrics
            processing_time = time.time() - start_time
            total_tokens = primary_tokens + secondary_tokens + synthesis_tokens
            estimated_cost = total_tokens * 0.00001  # Rough estimate, $0.01 per 1K tokens
            
            token_usage = TokenUsage(
                primary_model_tokens=primary_tokens,
                secondary_model_tokens=secondary_tokens,
                synthesis_model_tokens=synthesis_tokens,
                total_tokens=total_tokens,
                estimated_cost=estimated_cost
            )
            
            result = MultiModelResult(
                primary_summary=primary_summary,
                secondary_summary=secondary_summary,
                final_summary=final_summary,
                token_usage=token_usage,
                processing_time=processing_time,
                fallback_used=fallback_used,
                fallback_strategy=fallback_strategy,
                error_details=error_details
            )
            
            logger.info("Multi-model summarization completed",
                       processing_time=processing_time,
                       total_tokens=total_tokens,
                       fallback_used=fallback_used,
                       final_summary_length=len(final_summary))
            
            return result
            
        except Exception as e:
            logger.error("Multi-model pipeline failed completely", error=str(e))
            # Last resort fallback to single model
            try:
                final_summary = super().summarize(content)
                processing_time = time.time() - start_time
                
                token_usage = TokenUsage(
                    primary_model_tokens=0,
                    secondary_model_tokens=0,
                    synthesis_model_tokens=0,
                    total_tokens=len(content) // 4 + len(final_summary) // 4,
                    estimated_cost=0.0
                )
                
                return MultiModelResult(
                    primary_summary="",
                    secondary_summary="",
                    final_summary=final_summary,
                    token_usage=token_usage,
                    processing_time=processing_time,
                    fallback_used=True,
                    fallback_strategy=FallbackStrategy.SINGLE_MODEL,
                    error_details=f"Complete pipeline failure: {e}"
                )
            except Exception as fallback_error:
                logger.error("Even single-model fallback failed", error=str(fallback_error))
                raise Exception(f"Complete summarization failure: {e}; Fallback error: {fallback_error}")
    
    def summarize(self, content: str) -> str:
        """
        Main summarize method that maintains backward compatibility.
        
        Uses multi-model approach if enabled, otherwise falls back to single model.
        
        Args:
            content: Content to summarize
            
        Returns:
            Final summary string
        """
        if not self.is_multi_model_enabled:
            return super().summarize(content)
        
        try:
            result = self.multi_model_summarize(content)
            return result.final_summary
        except Exception as e:
            logger.error("Multi-model summarization failed, using single model fallback", error=str(e))
            return super().summarize(content)