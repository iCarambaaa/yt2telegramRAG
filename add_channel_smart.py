#!/usr/bin/env python3
"""
Smart channel setup tool that analyzes channel content and creates personalized prompts
"""

import sys
import os
import yaml
import yt_dlp
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ChannelAnalyzer:
    """AI-powered YouTube channel analyzer that deeply understands content and style"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': True,
            'subtitleslangs': ['-live_chat'],
            'skip_download': True,
            'playlist_items': '1:5'  # Analyze first 5 videos
        }
        
        # Initialize LLM client
        self.llm_client = OpenAI(
            api_key=os.getenv('LLM_PROVIDER_API_KEY'),
            base_url=os.getenv('BASE_URL', 'https://openrouter.ai/api/v1')
        )
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get comprehensive channel information with video content"""
        print(f"🔍 Fetching channel data: {channel_id}")
        
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
                info = ydl.extract_info(channel_url, download=False)
                
                channel_name = info.get('title', info.get('uploader', 'Unknown Channel'))
                description = info.get('description', '')
                entries = info.get('entries', [])[:5]
                
                print(f"✅ Found: {channel_name}")
                print(f"📊 Downloading subtitles from {len(entries)} recent videos...")
                
                # Get detailed video info with subtitles
                detailed_videos = []
                for entry in entries:
                    try:
                        video_info = ydl.extract_info(entry['url'], download=False)
                        
                        # Extract subtitle content
                        subtitle_content = ""
                        if 'automatic_captions' in video_info:
                            for lang, subs in video_info['automatic_captions'].items():
                                if subs:  # Take first available subtitle format
                                    sub_url = subs[0]['url']
                                    import requests
                                    response = requests.get(sub_url)
                                    if response.status_code == 200:
                                        subtitle_content = response.text[:5000]  # First 5000 chars
                                        break
                        
                        detailed_videos.append({
                            'title': video_info.get('title', ''),
                            'description': video_info.get('description', '')[:1000],  # First 1000 chars
                            'subtitles': subtitle_content,
                            'view_count': video_info.get('view_count', 0),
                            'upload_date': video_info.get('upload_date', '')
                        })
                        
                    except Exception as e:
                        print(f"⚠️ Skipping video due to error: {e}")
                        continue
                
                return {
                    'name': channel_name,
                    'id': channel_id,
                    'description': description,
                    'videos': detailed_videos
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def analyze_with_ai(self, channel_info: Dict) -> Dict:
        """Use AI to deeply analyze channel content and style"""
        print(f"🧠 AI analyzing {channel_info['name']} content and style...")
        
        # Prepare content for AI analysis
        analysis_content = self._prepare_content_for_analysis(channel_info)
        
        # AI analysis prompt
        analysis_prompt = f"""Analyze this YouTube channel based on the provided content. You have access to:
- Channel name and description
- Recent video titles, descriptions, and subtitle excerpts
- Your existing knowledge about this creator (if any)

Channel: {channel_info['name']}
Channel ID: {channel_info['id']}

{analysis_content}

Please provide a comprehensive analysis in JSON format with these fields:

{{
    "creator_background": "What you know about this creator, their expertise, background, and focus",
    "content_themes": ["primary", "secondary", "themes"],
    "content_type": "informational OR educational OR entertainment OR hybrid",
    "unique_style": "Detailed description of their distinctive communication style and approach",
    "storytelling_approach": "How they structure and present information",
    "target_audience": "Who watches this channel and why",
    "key_strengths": "What makes this creator special and worth following",
    "tone_and_personality": "Their characteristic tone and personality traits",
    "typical_content_structure": "How they typically organize their content",
    "language_and_terminology": "Specific words, phrases, or terminology they use",
    "summary_focus": "What aspects should be emphasized when summarizing - key facts, main insights, and unique perspectives"
}}

Focus on factual content capture while preserving the creator's unique style and approach. Be specific and detailed. Use your knowledge of this creator if you recognize them."""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=os.getenv('MODEL', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "You are an expert content analyst who understands YouTube creators and their unique styles."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3
            )
            
            # Parse JSON response
            analysis_text = response.choices[0].message.content
            
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_start = analysis_text.find('{')
            json_end = analysis_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = analysis_text[json_start:json_end]
                analysis = json.loads(json_str)
                
                print(f"✅ AI analysis complete")
                print(f"   Themes: {', '.join(analysis.get('content_themes', []))}")
                print(f"   Style: {analysis.get('tone_and_personality', 'Unknown')}")
                
                return analysis
            else:
                raise ValueError("Could not parse JSON from AI response")
                
        except Exception as e:
            print(f"❌ AI analysis failed: {e}")
            # Fallback to basic analysis
            return self._fallback_analysis(channel_info)
    
    def _prepare_content_for_analysis(self, channel_info: Dict) -> str:
        """Prepare channel content for AI analysis"""
        content_parts = []
        
        # Channel description
        if channel_info.get('description'):
            content_parts.append(f"CHANNEL DESCRIPTION:\n{channel_info['description'][:500]}")
        
        # Recent videos
        videos = channel_info.get('videos', [])
        for i, video in enumerate(videos[:5], 1):
            content_parts.append(f"\nVIDEO {i}:")
            content_parts.append(f"Title: {video.get('title', 'N/A')}")
            
            if video.get('description'):
                content_parts.append(f"Description: {video['description'][:300]}...")
            
            if video.get('subtitles'):
                # Clean subtitle content
                subtitle_text = video['subtitles'].replace('\n', ' ')
                # Remove VTT formatting
                subtitle_text = re.sub(r'<[^>]+>', '', subtitle_text)
                subtitle_text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', subtitle_text)
                subtitle_text = ' '.join(subtitle_text.split())  # Clean whitespace
                
                content_parts.append(f"Content excerpt: {subtitle_text[:800]}...")
        
        return '\n'.join(content_parts)
    
    def _fallback_analysis(self, channel_info: Dict) -> Dict:
        """Fallback analysis if AI fails"""
        return {
            "creator_background": "Unknown creator",
            "content_themes": ["general"],
            "unique_style": "Professional and informative",
            "storytelling_approach": "Direct presentation of information",
            "target_audience": "General audience interested in the topic",
            "key_strengths": "Knowledgeable content creation",
            "tone_and_personality": "Professional and engaging",
            "typical_content_structure": "Introduction, main content, conclusion",
            "language_and_terminology": "Clear and accessible language",
            "summary_focus": "Key facts and main insights"
        }
    


class PromptGenerator:
    """Generates AI-powered personalized prompts based on deep channel analysis"""
    
    def __init__(self):
        self.llm_client = OpenAI(
            api_key=os.getenv('LLM_PROVIDER_API_KEY'),
            base_url=os.getenv('BASE_URL', 'https://openrouter.ai/api/v1')
        )
    
    def generate_prompt(self, channel_info: Dict, analysis: Dict) -> str:
        """Generate highly personalized prompt based on AI analysis"""
        print(f"🎯 Generating personalized prompt for {channel_info['name']}...")
        
        prompt_generation_request = f"""Based on this detailed analysis of {channel_info['name']}, create a perfect summarization prompt that will extract key facts and insights while preserving their unique voice and style.

CHANNEL ANALYSIS:
{json.dumps(analysis, indent=2)}

Create a prompt that:
1. Extracts the key facts, insights, and concrete information from their content
2. Captures their distinctive communication style and personality
3. Focuses on the type of information their audience values most
4. Maintains their characteristic tone and approach
5. Preserves what makes them special while prioritizing factual content
6. Is specific enough to generate summaries that feel authentic to this creator

The prompt should prioritize factual content extraction while maintaining the creator's unique style.

Format the prompt as a clear instruction that will be used to summarize their video content. End with {{content}} placeholder.

Example structure:
"Extract the key facts and insights from this {channel_info['name']} video while maintaining [their specific style traits].

Focus on [what their audience cares about] and preserve [their unique characteristics].

[Any specific instructions based on their style]

{{content}}"

Make it specific to this creator, not generic."""
        
        try:
            response = self.llm_client.chat.completions.create(
                model=os.getenv('MODEL', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "You are an expert at creating personalized content summarization prompts that preserve creator authenticity."},
                    {"role": "user", "content": prompt_generation_request}
                ],
                temperature=0.4
            )
            
            generated_prompt = response.choices[0].message.content.strip()
            
            # Ensure it ends with {content}
            if not generated_prompt.endswith('{content}'):
                generated_prompt += '\n\n{content}'
            
            print(f"✅ Personalized prompt generated")
            return generated_prompt
            
        except Exception as e:
            print(f"❌ Prompt generation failed: {e}")
            # Fallback to simple prompt
            return self._fallback_prompt(channel_info['name'])
    
    def _fallback_prompt(self, channel_name: str) -> str:
        """Fallback prompt if AI generation fails"""
        return f"""Extract the key facts and insights from this {channel_name} video while preserving their unique style and perspective.

Focus on concrete information and maintain {channel_name}'s distinctive communication approach.

{{content}}"""

def create_channel_config(channel_info: Dict, analysis: Dict) -> Dict:
    """Create channel configuration based on AI analysis"""
    name = channel_info['name']
    # Create clean safe name: replace spaces/special chars with single underscore, remove consecutive underscores
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    
    return {
        'name': name,
        'channel_id': channel_info['id'],
        'db_path': f"yt2telegram/downloads/{safe_name}.db",
        'cookies_file': "COOKIES_FILE",
        'max_videos_to_fetch': 3,
        'retry_attempts': 3,
        'retry_delay_seconds': 5,
        'llm_config': {
            'llm_api_key_env': "LLM_PROVIDER_API_KEY",
            'llm_model_env': "MODEL",
            'llm_model': "gpt-4o-mini",
            'llm_base_url_env': "BASE_URL",
            'llm_base_url': "https://openrouter.ai/api/v1",
            'llm_prompt_template_path': f"yt2telegram/prompts/{safe_name}_summary.md"
        },
        'telegram_bots': [{
            'name': f"{name} Bot",
            'token_env': "TELEGRAM_BOT_TOKEN",
            'chat_id_env': f"{safe_name.upper()}_CHAT_ID"
        }],
        'subtitles': ["en"]
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python add_channel_smart.py <channel_id>")
        print("Example: python add_channel_smart.py UCbfYPyITQ-7l4upoX8nvctg")
        sys.exit(1)
    
    channel_id = sys.argv[1]
    
    print("🧠 Smart YouTube Channel Setup Tool")
    print("=" * 50)
    
    # Analyze channel with AI
    analyzer = ChannelAnalyzer()
    channel_info = analyzer.get_channel_info(channel_id)
    
    if not channel_info:
        print("❌ Failed to fetch channel data")
        sys.exit(1)
    
    analysis = analyzer.analyze_with_ai(channel_info)
    
    print(f"\n📊 AI Analysis Results:")
    print(f"   Background: {analysis.get('creator_background', 'Unknown')[:100]}...")
    print(f"   Themes: {', '.join(analysis.get('content_themes', []))}")
    print(f"   Style: {analysis.get('tone_and_personality', 'Unknown')[:50]}...")
    print(f"   Strengths: {analysis.get('key_strengths', 'Unknown')[:50]}...")
    
    # Generate AI-powered personalized prompt
    prompt_generator = PromptGenerator()
    prompt_content = prompt_generator.generate_prompt(channel_info, analysis)
    
    # Create configuration
    config = create_channel_config(channel_info, analysis)
    # Create clean safe name: replace spaces/special chars with single underscore, remove consecutive underscores
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', channel_info['name'].lower()).strip('_')
    
    # Create directories
    Path("yt2telegram/channels").mkdir(parents=True, exist_ok=True)
    Path("yt2telegram/prompts").mkdir(parents=True, exist_ok=True)
    
    # Save files
    config_path = f"yt2telegram/channels/{safe_name}.yml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    prompt_path = f"yt2telegram/prompts/{safe_name}_summary.md"
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt_content)
    
    # Update .env
    env_var = f"{safe_name.upper()}_CHAT_ID"
    with open(".env", 'a') as f:
        f.write(f'\n{env_var}="YOUR_CHAT_ID_HERE"  # Update with chat ID for {channel_info["name"]}\n')
    
    print(f"\n✅ Smart setup complete!")
    print(f"📁 Configuration: {config_path}")
    print(f"📝 Personalized prompt: {prompt_path}")
    print(f"📧 Added {env_var} to .env")
    print(f"\n🎯 Detected: {analysis.get('content_themes', ['general'])[0]} channel")
    print(f"🎨 Style: {analysis.get('unique_style', 'Professional')[:60]}...")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Update {env_var} in .env with your chat ID")
    print(f"   2. Test with: python run.py")

if __name__ == "__main__":
    main()