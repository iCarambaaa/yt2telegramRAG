#!/usr/bin/env python3
"""
Smart channel setup tool that analyzes channel content and creates personalized prompts
"""

import sys
import os
import yaml
import yt_dlp
import re
from pathlib import Path
from typing import Dict, List, Optional

class ChannelAnalyzer:
    """Analyzes YouTube channels to understand their style and content"""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': True,
            'subtitleslangs': ['-live_chat'],  # Get original language auto-captions, exclude live chat
            'skip_download': True,
            'playlist_items': '1:5'  # Analyze first 5 videos
        }
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get comprehensive channel information"""
        print(f"🔍 Analyzing channel: {channel_id}")
        
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
                info = ydl.extract_info(channel_url, download=False)
                
                channel_name = info.get('title', info.get('uploader', 'Unknown Channel'))
                description = info.get('description', '')
                entries = info.get('entries', [])[:5]  # First 5 videos
                
                print(f"✅ Found: {channel_name}")
                print(f"📊 Analyzing {len(entries)} recent videos...")
                
                return {
                    'name': channel_name,
                    'id': channel_id,
                    'description': description,
                    'videos': entries
                }
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def analyze_content_style(self, channel_info: Dict) -> Dict:
        """Analyze channel's content style and themes"""
        videos = channel_info.get('videos', [])
        titles = [v.get('title', '') for v in videos if v.get('title')]
        descriptions = [v.get('description', '') for v in videos if v.get('description')]
        
        # Combine all text for analysis
        all_text = ' '.join(titles + descriptions).lower()
        
        # Detect content themes
        themes = self._detect_themes(all_text)
        style = self._detect_style(titles, descriptions)
        tone = self._detect_tone(all_text)
        
        return {
            'themes': themes,
            'style': style,
            'tone': tone,
            'sample_titles': titles[:3]
        }
    
    def _detect_themes(self, text: str) -> List[str]:
        """Detect main content themes"""
        theme_patterns = {
            'crypto': ['bitcoin', 'crypto', 'blockchain', 'trading', 'defi', 'nft', 'ethereum'],
            'ai_research': ['ai', 'machine learning', 'neural', 'paper', 'research', 'model', 'algorithm'],
            'space_tech': ['space', 'mars', 'rocket', 'satellite', 'colony', 'civilization', 'megastructure'],
            'geopolitics': ['politics', 'war', 'election', 'government', 'policy', 'international', 'conflict'],
            'tech_news': ['tech', 'startup', 'innovation', 'breakthrough', 'development', 'technology'],
            'finance': ['market', 'economy', 'stock', 'investment', 'financial', 'banking', 'fed']
        }
        
        detected_themes = []
        for theme, keywords in theme_patterns.items():
            if sum(text.count(keyword) for keyword in keywords) > 2:
                detected_themes.append(theme)
        
        return detected_themes or ['general']
    
    def _detect_style(self, titles: List[str], descriptions: List[str]) -> Dict:
        """Detect presentation style"""
        all_titles = ' '.join(titles).lower()
        
        style = {
            'analytical': bool(re.search(r'\b(analysis|breakdown|explained|deep dive)\b', all_titles)),
            'enthusiastic': bool(re.search(r'[!]{2,}|amazing|incredible|breakthrough', all_titles)),
            'educational': bool(re.search(r'\b(how to|tutorial|guide|learn)\b', all_titles)),
            'news_focused': bool(re.search(r'\b(breaking|news|update|latest)\b', all_titles)),
            'technical': bool(re.search(r'\b(technical|specs|data|metrics)\b', all_titles)),
            'storytelling': len([t for t in titles if len(t.split()) > 8]) > len(titles) * 0.6
        }
        
        return {k: v for k, v in style.items() if v}
    
    def _detect_tone(self, text: str) -> str:
        """Detect overall tone"""
        if any(word in text for word in ['exciting', 'amazing', 'incredible', 'breakthrough']):
            return 'enthusiastic'
        elif any(word in text for word in ['analysis', 'data', 'research', 'study']):
            return 'analytical'
        elif any(word in text for word in ['breaking', 'urgent', 'alert', 'developing']):
            return 'urgent'
        else:
            return 'informative'

class PromptGenerator:
    """Generates personalized prompts based on channel analysis"""
    
    def generate_prompt(self, channel_info: Dict, analysis: Dict) -> str:
        """Generate simple, flexible prompt for any channel"""
        channel_name = channel_info['name']
        
        return f"""Extract the key facts and insights from this {channel_name} video while preserving their unique style and perspective.

Focus on concrete information and maintain {channel_name}'s distinctive communication approach.

{{content}}"""

def create_channel_config(channel_info: Dict, analysis: Dict) -> Dict:
    """Create channel configuration based on analysis"""
    name = channel_info['name']
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
    
    # Determine schedule based on content type
    schedule = 'daily' if 'news' in analysis['themes'] or 'geopolitics' in analysis['themes'] else 'weekly'
    
    return {
        'name': name,
        'channel_id': channel_info['id'],
        'schedule': schedule,
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
    
    # Analyze channel
    analyzer = ChannelAnalyzer()
    channel_info = analyzer.get_channel_info(channel_id)
    
    if not channel_info:
        print("❌ Failed to analyze channel")
        sys.exit(1)
    
    analysis = analyzer.analyze_content_style(channel_info)
    
    print(f"\n📊 Analysis Results:")
    print(f"   Themes: {', '.join(analysis['themes'])}")
    print(f"   Style: {', '.join(analysis['style'].keys())}")
    print(f"   Tone: {analysis['tone']}")
    
    # Generate personalized prompt
    prompt_generator = PromptGenerator()
    prompt_content = prompt_generator.generate_prompt(channel_info, analysis)
    
    # Create configuration
    config = create_channel_config(channel_info, analysis)
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', channel_info['name'].lower())
    
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
    print(f"\n🎯 Detected: {analysis['themes'][0]} channel with {analysis['tone']} tone")
    print(f"📅 Recommended schedule: {config['schedule']}")
    
    print(f"\n🚀 Next steps:")
    print(f"   1. Update {env_var} in .env with your chat ID")
    print(f"   2. Test with: python run.py")

if __name__ == "__main__":
    main()