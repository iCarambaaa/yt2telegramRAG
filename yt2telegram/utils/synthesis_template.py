"""
Synthesis template loading and formatting utilities for multi-model summarization.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)


class SynthesisTemplateLoader:
    """Handles loading and formatting of synthesis prompt templates."""
    
    DEFAULT_TEMPLATE_PATH = "yt2telegram/prompts/synthesis_template.md"
    
    def __init__(self, template_path: Optional[str] = None):
        """
        Initialize the template loader.
        
        Args:
            template_path: Path to custom synthesis template. If None, uses default.
        """
        self.template_path = template_path or self.DEFAULT_TEMPLATE_PATH
        self._template_content: Optional[str] = None
    
    def load_template(self) -> str:
        """
        Load the synthesis template from file.
        
        Returns:
            Template content as string
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template is empty
        """
        if self._template_content is None:
            try:
                template_path = Path(self.template_path)
                if not template_path.exists():
                    raise FileNotFoundError(f"Synthesis template not found: {self.template_path}")
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    self._template_content = f.read().strip()
                
                if not self._template_content:
                    raise ValueError(f"Synthesis template is empty: {self.template_path}")
                
                logger.info("Loaded synthesis template", path=self.template_path, 
                           length=len(self._template_content))
                
            except Exception as e:
                logger.error("Failed to load synthesis template", path=self.template_path, error=str(e))
                raise
        
        return self._template_content
    
    def format_template(self, 
                       creator_context: str,
                       summary_a: str,
                       summary_b: str,
                       original_content: str,
                       model_a: str = "Model A",
                       model_b: str = "Model B") -> str:
        """
        Format the synthesis template with provided content.
        
        Args:
            creator_context: Context about the creator's style and voice
            summary_a: First summary to synthesize
            summary_b: Second summary to synthesize
            original_content: Original transcript for conflict resolution
            model_a: Name of first model (for reference)
            model_b: Name of second model (for reference)
            
        Returns:
            Formatted template ready for LLM
            
        Raises:
            ValueError: If any required parameter is empty
        """
        # Validate inputs
        if not creator_context.strip():
            raise ValueError("Creator context cannot be empty")
        if not summary_a.strip():
            raise ValueError("Summary A cannot be empty")
        if not summary_b.strip():
            raise ValueError("Summary B cannot be empty")
        if not original_content.strip():
            raise ValueError("Original content cannot be empty")
        
        template = self.load_template()
        
        # Truncate original content if too long to avoid token limits
        max_content_chars = 30000  # Leave room for summaries and template
        if len(original_content) > max_content_chars:
            logger.info("Truncating original content for synthesis", 
                       original_length=len(original_content), 
                       max_chars=max_content_chars)
            original_content = original_content[:max_content_chars] + "...\n\n[Content truncated due to length]"
        
        try:
            formatted_template = template.format(
                creator_context=creator_context,
                summary_a=summary_a,
                summary_b=summary_b,
                original_content=original_content,
                model_a=model_a,
                model_b=model_b
            )
            
            logger.info("Formatted synthesis template", 
                       template_length=len(formatted_template),
                       creator_context_length=len(creator_context),
                       summary_a_length=len(summary_a),
                       summary_b_length=len(summary_b),
                       original_content_length=len(original_content))
            
            return formatted_template
            
        except KeyError as e:
            logger.error("Template formatting failed - missing placeholder", error=str(e))
            raise ValueError(f"Template contains invalid placeholder: {e}")
        except Exception as e:
            logger.error("Template formatting failed", error=str(e))
            raise


class CreatorContextExtractor:
    """Extracts creator-specific context from existing prompt templates."""
    
    @staticmethod
    def extract_from_prompt_template(prompt_template_path: str) -> str:
        """
        Extract creator context from an existing prompt template.
        
        Args:
            prompt_template_path: Path to the creator's prompt template
            
        Returns:
            Extracted creator context describing their style and voice
            
        Raises:
            FileNotFoundError: If prompt template doesn't exist
        """
        try:
            template_path = Path(prompt_template_path)
            if not template_path.exists():
                raise FileNotFoundError(f"Prompt template not found: {prompt_template_path}")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Extract creator-specific sections from the template
            context_parts = []
            
            # Look for voice/style preservation sections
            lines = template_content.split('\n')
            in_voice_section = False
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Start of voice/style section
                if any(keyword in line_lower for keyword in [
                    'preserve', 'voice', 'style', 'tone', 'characteristic', 
                    'maintain', 'enthusiasm', 'personality'
                ]):
                    in_voice_section = True
                    context_parts.append(line.strip())
                    continue
                
                # End of section (empty line or new major section)
                if in_voice_section:
                    if line.strip() == '' or line.startswith('**') and 'format' in line_lower:
                        in_voice_section = False
                        continue
                    context_parts.append(line.strip())
            
            # If no specific voice section found, extract from general instructions
            if not context_parts:
                # Look for any creator-specific mentions
                for line in lines:
                    if any(keyword in line.lower() for keyword in [
                        'channel', 'creator', 'author', 'style', 'voice', 'tone'
                    ]) and not line.startswith('#'):
                        context_parts.append(line.strip())
            
            # Fallback to generic context if nothing found
            if not context_parts:
                creator_name = template_path.stem.replace('_summary', '').replace('_', ' ').title()
                context_parts = [f"Maintain {creator_name}'s distinctive voice and style from the original content."]
            
            context = '\n'.join(context_parts)
            
            logger.info("Extracted creator context", 
                       template_path=prompt_template_path,
                       context_length=len(context))
            
            return context
            
        except Exception as e:
            logger.error("Failed to extract creator context", 
                        template_path=prompt_template_path, 
                        error=str(e))
            # Return generic fallback
            return "Maintain the creator's distinctive voice, style, and personality from the original content."