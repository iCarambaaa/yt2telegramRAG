import re
import os
import yaml
from typing import Any, List, Dict, Optional

class ValidationError(Exception):
    pass

class InputValidator:
    @staticmethod
    def validate_telegram_chat_id(chat_id: Any) -> int:
        """Validate and convert telegram chat ID to integer"""
        try:
            chat_id_int = int(chat_id)
            return chat_id_int
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid chat ID format: {chat_id}")
    
    @staticmethod
    def validate_youtube_channel_id(channel_id: str) -> str:
        """Validate YouTube channel ID format"""
        if not channel_id or not isinstance(channel_id, str):
            raise ValidationError("Channel ID must be a non-empty string")
        
        # YouTube channel IDs are typically 24 characters starting with UC
        if not re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_id):
            raise ValidationError(f"Invalid YouTube channel ID format: {channel_id}")
        
        return channel_id

    @staticmethod
    def validate_multi_model_config(multi_model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate multi-model configuration"""
        if not isinstance(multi_model_config, dict):
            raise ValidationError("Multi-model configuration must be a dictionary")
        
        # Check if multi-model is enabled
        if not multi_model_config.get('enabled', False):
            return multi_model_config
        
        # Required fields for enabled multi-model
        required_fields = ['primary_model', 'secondary_model', 'synthesis_model']
        for field in required_fields:
            if not multi_model_config.get(field):
                raise ValidationError(f"Multi-model configuration missing required field: {field}")
        
        # Validate model names
        valid_models = {
            # OpenAI models
            'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo',
            # Anthropic models
            'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229',
            'claude-3-sonnet-20240229', 'claude-3-haiku-20240307',
            # Other common models
            'llama-3.1-405b-instruct', 'llama-3.1-70b-instruct', 'llama-3.1-8b-instruct'
        }
        
        for model_type in ['primary_model', 'secondary_model', 'synthesis_model']:
            model_name = multi_model_config[model_type]
            if not isinstance(model_name, str) or not model_name.strip():
                raise ValidationError(f"Invalid {model_type}: must be a non-empty string")
        
        # Validate synthesis template path
        synthesis_template_path = multi_model_config.get('synthesis_prompt_template_path')
        if synthesis_template_path and not os.path.exists(synthesis_template_path):
            raise ValidationError(f"Synthesis template file not found: {synthesis_template_path}")
        
        # Validate cost threshold
        cost_threshold = multi_model_config.get('cost_threshold_tokens')
        if cost_threshold is not None:
            if not isinstance(cost_threshold, int) or cost_threshold <= 0:
                raise ValidationError("cost_threshold_tokens must be a positive integer")
            if cost_threshold < 1000:
                raise ValidationError("cost_threshold_tokens should be at least 1000 for reasonable operation")
        
        # Validate fallback strategy
        fallback_strategy = multi_model_config.get('fallback_strategy', 'best_summary')
        valid_strategies = ['best_summary', 'primary_summary', 'single_model']
        if fallback_strategy not in valid_strategies:
            raise ValidationError(f"Invalid fallback_strategy: {fallback_strategy}. Must be one of: {valid_strategies}")
        
        # Validate temperature
        temperature = multi_model_config.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                raise ValidationError("temperature must be a number between 0 and 2")
        
        # Validate top_p
        top_p = multi_model_config.get('top_p')
        if top_p is not None:
            if not isinstance(top_p, (int, float)) or top_p <= 0 or top_p > 1:
                raise ValidationError("top_p must be a number between 0 and 1")
        
        return multi_model_config
    
    @staticmethod
    def validate_api_key_availability(multi_model_config: Dict[str, Any]) -> List[str]:
        """Validate that required API keys are available for multi-model configuration"""
        if not multi_model_config.get('enabled', False):
            return []
        
        warnings = []
        
        # Get all models used
        models = [
            multi_model_config.get('primary_model'),
            multi_model_config.get('secondary_model'),
            multi_model_config.get('synthesis_model')
        ]
        
        # Check for required API keys based on model providers
        openai_models = {'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo'}
        anthropic_models = {
            'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229',
            'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'
        }
        
        needs_openai = any(model in openai_models for model in models if model)
        needs_anthropic = any(model in anthropic_models for model in models if model)
        
        # Check for OpenRouter (can handle multiple providers)
        has_openrouter = bool(os.getenv('LLM_PROVIDER_API_KEY'))
        
        # Check for direct provider keys
        has_openai_key = bool(os.getenv('OPENAI_API_KEY'))
        has_anthropic_key = bool(os.getenv('ANTHROPIC_API_KEY'))
        
        if needs_openai and not (has_openrouter or has_openai_key):
            warnings.append("OpenAI models detected but no OPENAI_API_KEY or LLM_PROVIDER_API_KEY found")
        
        if needs_anthropic and not (has_openrouter or has_anthropic_key):
            warnings.append("Anthropic models detected but no ANTHROPIC_API_KEY or LLM_PROVIDER_API_KEY found")
        
        return warnings
    
    @staticmethod
    def validate_channel_multi_model_setup(channel_config_path: str) -> Dict[str, Any]:
        """Comprehensive validation of channel multi-model setup"""
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        try:
            # Load and parse channel configuration
            with open(channel_config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            llm_config = config_data.get('llm_config', {})
            multi_model_config = llm_config.get('multi_model', {})
            
            if not multi_model_config.get('enabled', False):
                validation_result['recommendations'].append(
                    "Multi-model is disabled. Enable it for enhanced summary quality."
                )
                return validation_result
            
            # Validate multi-model configuration
            try:
                InputValidator.validate_multi_model_config(multi_model_config)
            except ValidationError as e:
                validation_result['errors'].append(str(e))
                validation_result['valid'] = False
            
            # Check API key availability
            api_warnings = InputValidator.validate_api_key_availability(multi_model_config)
            validation_result['warnings'].extend(api_warnings)
            
            # Check synthesis template
            synthesis_template_path = multi_model_config.get('synthesis_prompt_template_path')
            if synthesis_template_path:
                if not os.path.exists(synthesis_template_path):
                    validation_result['errors'].append(
                        f"Synthesis template not found: {synthesis_template_path}"
                    )
                    validation_result['valid'] = False
            else:
                validation_result['warnings'].append(
                    "No synthesis template specified. Using default template."
                )
            
            # Performance recommendations
            primary_model = multi_model_config.get('primary_model', '')
            secondary_model = multi_model_config.get('secondary_model', '')
            synthesis_model = multi_model_config.get('synthesis_model', '')
            
            # Check for model diversity
            if primary_model == secondary_model:
                validation_result['warnings'].append(
                    "Primary and secondary models are the same. Consider using different models for better diversity."
                )
            
            # Check for cost-effective setup
            expensive_models = {'gpt-4o', 'claude-3-5-sonnet-20241022', 'claude-3-opus-20240229'}
            if primary_model in expensive_models and secondary_model in expensive_models:
                validation_result['recommendations'].append(
                    "Consider using a cheaper model for primary or secondary to reduce costs."
                )
            
            # Check cost threshold
            cost_threshold = multi_model_config.get('cost_threshold_tokens')
            if not cost_threshold:
                validation_result['recommendations'].append(
                    "Consider setting cost_threshold_tokens to prevent unexpected high costs."
                )
            elif cost_threshold < 10000:
                validation_result['warnings'].append(
                    "Cost threshold is very low and may cause frequent fallbacks to single-model."
                )
            
        except Exception as e:
            validation_result['errors'].append(f"Failed to validate configuration: {str(e)}")
            validation_result['valid'] = False
        
        return validation_result

class Sanitizer:

    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters according to Telegram Bot API"""
        if not text:
            return text
        
        # Telegram HTML formatting requires escaping these characters
        # According to: https://core.telegram.org/bots/api#html-style
        html_escapes = {
            '&': '&amp;',   # Must be first to avoid double-escaping
            '<': '&lt;',
            '>': '&gt;',
        }
        
        for char, escape in html_escapes.items():
            text = text.replace(char, escape)
        
        return text
    
    @staticmethod
    def escape_markdown_v2(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2 according to Bot API"""
        if not text:
            return text
        
        # According to Telegram Bot API, these characters must be escaped in MarkdownV2:
        # _*[]()~`>#+-=|{}.!
        # But we need to be careful not to escape characters that are part of formatting
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        escaped_text = ""
        
        for char in text:
            if char in escape_chars:
                escaped_text += f"\\{char}"
            else:
                escaped_text += char
        
        return escaped_text
    

    
    @staticmethod
    def clean_for_telegram(text: str) -> str:
        """Clean markdown text for Telegram messages"""
        if not text:
            return text
        
        # Clean problematic patterns while preserving markdown
        text = re.sub(r'[~{}+=\[\]]', '', text)  # Remove special chars
        text = re.sub(r'[|]', ' ', text)  # Remove table separators
        text = re.sub(r'[-]{3,}', '\n━━━━━━━━━━\n', text)  # Convert horizontal rules to visual separator
        text = re.sub(r'>\s*', '', text, flags=re.MULTILINE)  # Remove blockquotes
        
        # Fix spacing issues
        text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces/tabs but keep newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Max 2 consecutive newlines
        
        # Fix punctuation
        text = re.sub(r'\.{3,}', '...', text)  # Normalize ellipsis
        text = re.sub(r'!{2,}', '!', text)  # Single exclamation
        text = re.sub(r'\?{2,}', '?', text)  # Single question mark
        text = re.sub(r'--+', ' — ', text)  # Replace dashes with em-dash
        
        # Final cleanup
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        text = text.strip()
        
        return text
    

    @staticmethod
    def convert_markdown_to_clean_html(text: str) -> str:
        """Convert simple markdown formatting to clean Telegram HTML"""
        if not text:
            return text
        
        # Convert **bold** to <b>bold</b>
        text = re.sub(r'\*\*([^*\n]+?)\*\*', r'<b>\1</b>', text)
        
        # Convert `code` to <code>code</code>
        text = re.sub(r'`([^`\n]+?)`', r'<code>\1</code>', text)
        
        # Escape any remaining HTML characters in the text
        # But preserve our newly created <b> and <code> tags
        parts = re.split(r'(</?(?:b|code)>)', text)
        escaped_parts = []
        
        for part in parts:
            if part in ['<b>', '</b>', '<code>', '</code>']:
                escaped_parts.append(part)
            else:
                # Escape HTML in regular text but preserve line breaks and structure
                escaped_part = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                escaped_parts.append(escaped_part)
        
        return ''.join(escaped_parts)
    
    @staticmethod
    def validate_telegram_message(text: str) -> bool:
        """Validate message meets Telegram Bot API requirements"""
        if not text:
            return False
        
        # Telegram message limits according to Bot API
        MAX_MESSAGE_LENGTH = 4096
        
        if len(text) > MAX_MESSAGE_LENGTH:
            return False
        
        return True
    
    @staticmethod
    def split_for_telegram(text: str, max_length: int = 3800) -> List[str]:
        """Split text into multiple messages that fit Telegram's limits while preserving all content"""
        if len(text) <= max_length:
            return [text]
        
        messages = []
        remaining_text = text
        part_number = 1
        
        while remaining_text:
            if len(remaining_text) <= max_length:
                # Last part
                if len(messages) > 0:  # Only add part number if there are multiple parts
                    messages.append(f"📄 Part {part_number}/{part_number}\n\n{remaining_text}")
                else:
                    messages.append(remaining_text)
                break
            
            # Find the best split point
            chunk = remaining_text[:max_length]
            
            # Look for good split points in order of preference
            split_points = [
                (chunk.rfind('\n\n'), 'paragraph'),  # Paragraph break
                (chunk.rfind('. '), 'sentence'),     # Sentence end
                (chunk.rfind('! '), 'sentence'),     # Exclamation
                (chunk.rfind('? '), 'sentence'),     # Question
                (chunk.rfind('\n'), 'line'),         # Line break
                (chunk.rfind(' '), 'word')           # Word boundary
            ]
            
            split_pos = max_length
            for pos, split_type in split_points:
                if pos > max_length * 0.6:  # Keep at least 60% of chunk
                    split_pos = pos + (1 if split_type == 'sentence' else 0)
                    break
            
            # Calculate total parts estimate (will be corrected later)
            total_parts = max(2, (len(text) // max_length) + 1)
            
            # Add this part
            part_text = remaining_text[:split_pos].strip()
            messages.append(f"📄 Part {part_number}/{total_parts}\n\n{part_text}")
            
            # Move to next part
            remaining_text = remaining_text[split_pos:].strip()
            part_number += 1
        
        # Fix part numbers now that we know the actual total
        actual_total = len(messages)
        if actual_total > 1:
            for i in range(len(messages)):
                # Replace the estimated total with the actual total
                old_pattern = re.search(r'📄 Part (\d+)/(\d+)', messages[i])
                if old_pattern:
                    messages[i] = re.sub(r'📄 Part (\d+)/(\d+)', f'📄 Part {i+1}/{actual_total}', messages[i], 1)
        
        return messages
    
    @staticmethod
    def truncate_for_telegram(text: str, max_length: int = 3800) -> str:
        """Legacy truncate method - use split_for_telegram instead to preserve all content"""
        parts = Sanitizer.split_for_telegram(text, max_length)
        return parts[0]  # Return only first part for backward compatibility