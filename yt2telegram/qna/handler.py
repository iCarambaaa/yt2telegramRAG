"""Q&A handler for processing user questions and generating responses."""
import requests
import json
from typing import List, Dict, Any
from .database import DatabaseQuery

class QnAHandler:
    """Handles Q&A processing with OpenRouter API integration."""
    
    def __init__(self, db_path: str, openrouter_key: str):
        """Initialize Q&A handler."""
        self.db = DatabaseQuery(db_path)
        self.openrouter_key = openrouter_key
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def search_and_answer(self, question: str) -> str:
        """Search content and generate answer using LLM."""
        # Search for relevant content
        search_results = self.db.search_content(question, limit=3)
        
        if not search_results:
            return "I couldn't find any relevant content for your question. Try rephrasing or ask about specific topics."
        
        # Prepare context for LLM
        context = self._prepare_context(search_results)
        
        # Generate answer using OpenRouter
        return self._generate_answer(question, context)
    
    def get_latest_summary(self) -> str:
        """Get summary of latest videos."""
        latest_videos = self.db.get_latest_videos(limit=3)
        
        if not latest_videos:
            return "No videos found in the database."
        
        response = "📺 **Latest Videos:**\n\n"
        for video in latest_videos:
            response += f"**{video['title']}**\n"
            response += f"📅 {video['upload_date']}\n"
            response += f"📝 {video['summary'][:200]}...\n"
            response += f"🔗 [Watch]({video['url']})\n\n"
        
        return response
    
    def search_content(self, query: str) -> str:
        """Search for specific content."""
        results = self.db.search_content(query, limit=5)
        
        if not results:
            return f"No results found for '{query}'."
        
        response = f"🔍 **Search Results for '{query}':**\n\n"
        
        for result in results[:3]:  # Limit to 3 results
            response += f"**{result['title']}**"
            if result['type'] == 'subtitle':
                response += f" (at {result.get('timestamp', 'N/A')})"
            response += "\n"
            
            content = result['content'][:150]
            if len(result['content']) > 150:
                content += "..."
            response += f"{content}\n"
            response += f"🔗 [Watch]({result['url']})\n\n"
        
        return response
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Prepare context from search results."""
        context = "Relevant content found:\n\n"
        
        for result in search_results:
            context += f"Title: {result['title']}\n"
            context += f"Type: {result['type']}\n"
            context += f"Content: {result['content'][:500]}...\n"
            context += f"URL: {result['url']}\n\n"
        
        return context
    
    def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using OpenRouter API."""
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "YouTube Q&A Bot"
        }
        
        prompt = f"""You are a helpful assistant answering questions about YouTube videos based on their summaries and subtitles.

Context from videos:
{context}

User Question: {question}

Please provide a clear, concise answer based on the provided context. If the context doesn't contain enough information, say so. Include relevant video titles and timestamps when possible."""
        
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful Q&A assistant for YouTube video content."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            answer = data['choices'][0]['message']['content']
            
            return answer
            
        except requests.exceptions.RequestException as e:
            return f"Sorry, I encountered an error generating the answer: {str(e)}"
        except (KeyError, IndexError):
            return "Sorry, I couldn't generate an answer at the moment. Please try again."