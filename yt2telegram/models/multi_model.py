from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum


class FallbackStrategy(Enum):
    """Strategies for handling multi-model failures"""
    BEST_SUMMARY = "best_summary"      # Select better of two summaries
    PRIMARY_SUMMARY = "primary_summary" # Always use primary model result
    SINGLE_MODEL = "single_model"      # Fallback to original approach


@dataclass
class TokenUsage:
    """Tracks token consumption across multi-model pipeline"""
    primary_model_tokens: int
    secondary_model_tokens: int
    synthesis_model_tokens: int
    total_tokens: int
    estimated_cost: float
    
    def __post_init__(self):
        """Validate token counts and calculate total if not provided"""
        if self.total_tokens == 0:
            self.total_tokens = (
                self.primary_model_tokens + 
                self.secondary_model_tokens + 
                self.synthesis_model_tokens
            )


@dataclass
class ModelConfig:
    """Configuration for individual model in multi-model pipeline"""
    model_name: str
    api_key_env: str
    base_url_env: str
    max_tokens: int = 2000
    temperature: float = 0.7
    
    def __post_init__(self):
        """Validate model configuration"""
        if not self.model_name:
            raise ValueError("model_name cannot be empty")
        if not self.api_key_env:
            raise ValueError("api_key_env cannot be empty")
        if not self.base_url_env:
            raise ValueError("base_url_env cannot be empty")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")


@dataclass
class MultiModelResult:
    """Result of multi-model summarization pipeline"""
    primary_summary: str
    secondary_summary: str
    final_summary: str
    token_usage: TokenUsage
    processing_time: float
    fallback_used: bool
    fallback_strategy: Optional[FallbackStrategy] = None
    error_details: Optional[str] = None
    
    def __post_init__(self):
        """Validate multi-model result"""
        if not self.final_summary:
            raise ValueError("final_summary cannot be empty")
        if self.processing_time < 0:
            raise ValueError("processing_time cannot be negative")
        if self.fallback_used and not self.fallback_strategy:
            raise ValueError("fallback_strategy must be specified when fallback_used is True")