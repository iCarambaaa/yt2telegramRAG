import re
from typing import Dict, Any, Optional
from datetime import datetime

from ..utils.logging_config import LoggerFactory
from .enhanced_telegram_service import EnhancedTelegramService, MessageType

logger = LoggerFactory.create_logger(__name__)

class TelegramQnAHandler:
    """
    Handler for QnA interactions through Telegram.
    
    Features:
    - Question detection and processing
    - Integration with existing QnA system
    - Conversation threading
    - Response formatting for Telegram
    
    CRITICAL: Core QnA integration for bidirectional communication
    DEPENDENCIES: EnhancedTelegramService, QnA system
    FALLBACK: Log questions if QnA system unavailable
    """
    
    def __init__(self, telegram_service: EnhancedTelegramService, qna_service=None):
        self.telegram_service = telegram_service
        self.qna_service = qna_service
        
        # Question patterns
        self.question_patterns = [
            r'\?$',  # Ends with question mark
            r'^(what|how|why|when|where|who|which|can|could|would|should|is|are|do|does|did)',  # Question words
            r'(explain|tell me|help|show)',  # Request words
        ]
        
        # Register as webhook handler
        self.telegram_service.register_webhook_handler("qna", self.handle_message)
        
        logger.info("Telegram QnA handler initialized")
    
    async def handle_message(self, chat_id: str, message_text: str, message_data: Dict[str, Any]):
        """Handle incoming Telegram message for QnA processing"""
        try:
            # Check if message looks like a question
            if not self._is_question(message_text):
                return
            
            user_info = message_data.get("from", {})
            user_id = str(user_info.get("id", ""))
            username = user_info.get("username", "Unknown")
            
            logger.info("Processing QnA question from Telegram", 
                       chat_id=chat_id, user_id=user_id, username=username)
            
            # Process question through QnA system
            if self.qna_service:
                try:
                    # Get QnA response
                    response = await self._process_question(
                        question=message_text,
                        chat_id=chat_id,
                        user_id=user_id,
                        context={"source": "telegram", "username": username}
                    )
                    
                    if response:
                        # Send response back to Telegram
                        await self.telegram_service.send_message_to_chat(
                            chat_id=chat_id,
                            message=response,
                            message_type=MessageType.QNA_RESPONSE,
                            parse_mode="HTML"
                        )
                        
                        logger.info("QnA response sent to Telegram", 
                                   chat_id=chat_id, user_id=user_id)
                    else:
                        # Send fallback response
                        fallback_msg = "I'm sorry, I couldn't find a good answer to your question. Please try rephrasing or ask about a specific video or topic."
                        await self.telegram_service.send_message_to_chat(
                            chat_id=chat_id,
                            message=fallback_msg,
                            message_type=MessageType.QNA_RESPONSE
                        )
                
                except Exception as e:
                    logger.error("Error processing QnA question", 
                               chat_id=chat_id, user_id=user_id, error=str(e))
                    
                    # Send error response
                    error_msg = "I'm experiencing some technical difficulties. Please try again later."
                    await self.telegram_service.send_message_to_chat(
                        chat_id=chat_id,
                        message=error_msg,
                        message_type=MessageType.QNA_RESPONSE
                    )
            else:
                # QnA service not available
                logger.warning("QnA service not available", chat_id=chat_id)
                
                unavailable_msg = "The QnA system is currently unavailable. Please try again later or use the web interface."
                await self.telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=unavailable_msg,
                    message_type=MessageType.SYSTEM_NOTIFICATION
                )
        
        except Exception as e:
            logger.error("Error in QnA handler", chat_id=chat_id, error=str(e))
    
    def _is_question(self, text: str) -> bool:
        """Determine if text looks like a question"""
        if not text or len(text.strip()) < 5:
            return False
        
        text_lower = text.lower().strip()
        
        # Check against question patterns
        for pattern in self.question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    async def _process_question(self, question: str, chat_id: str, user_id: str, 
                               context: Dict[str, Any]) -> Optional[str]:
        """Process question through QnA system"""
        try:
            if not self.qna_service:
                # Try to use the existing QnA system directly
                return await self._process_with_existing_qna(question, context)
            
            # Use configured QnA service
            response = await self.qna_service.process_question(
                question=question,
                user_id=user_id,
                context=context
            )
            
            return response
        
        except Exception as e:
            logger.error("Error processing question through QnA service", 
                        question=question, error=str(e))
            return None
    
    async def _process_with_existing_qna(self, question: str, context: Dict[str, Any]) -> Optional[str]:
        """Process question using the existing QnA system"""
        try:
            import os
            import sqlite3
            from typing import List, Dict, Any
            
            # Search for relevant content across available channels
            search_results = []
            
            # Get available channel databases
            downloads_dir = "yt2telegram/downloads"
            if os.path.exists(downloads_dir):
                for file in os.listdir(downloads_dir):
                    if file.endswith('.db'):
                        db_path = os.path.join(downloads_dir, file)
                        try:
                            results = self._search_channel_database(db_path, question)
                            search_results.extend(results)
                        except Exception as e:
                            logger.warning(f"Failed to search {db_path}", error=str(e))
            
            if not search_results:
                return "I couldn't find any relevant information to answer your question. Try asking about specific topics or videos."
            
            # Sort by relevance and generate response
            search_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            top_results = search_results[:2]
            
            # Generate response
            response_parts = []
            for result in top_results:
                if result['type'] == 'summary':
                    response_parts.append(f"📺 *{result['title']}*\n{result['content'][:300]}...")
                elif result['type'] == 'subtitle':
                    timestamp = result.get('timestamp', 'N/A')
                    response_parts.append(f"📺 *{result['title']}* (at {timestamp})\n{result['content'][:200]}...")
            
            if response_parts:
                response = "\n\n".join(response_parts)
                if len(top_results) < len(search_results):
                    response += f"\n\n_Found {len(search_results)} total results. Showing top {len(top_results)}._"
                return response
            else:
                return "I found some relevant videos but couldn't extract a clear answer. Please try rephrasing your question."
        
        except Exception as e:
            logger.error("Error in existing QnA processing", error=str(e))
            return None
    
    def _search_channel_database(self, db_path: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for content in a channel database"""
        results = []
        
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Search in video summaries
                cursor = conn.execute("""
                    SELECT video_id, title, summary, upload_date, url
                    FROM videos
                    WHERE summary LIKE ? OR title LIKE ?
                    ORDER BY upload_date DESC
                    LIMIT ?
                """, (f'%{query}%', f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    relevance_score = self._calculate_simple_relevance(query, row['title'], row['summary'])
                    results.append({
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'content': row['summary'],
                        'url': row['url'],
                        'type': 'summary',
                        'upload_date': row['upload_date'],
                        'relevance_score': relevance_score
                    })
                
                # Search in subtitles if available
                try:
                    cursor = conn.execute("""
                        SELECT v.video_id, v.title, s.content, s.start_time, v.upload_date, v.url
                        FROM videos v
                        JOIN subtitles s ON v.video_id = s.video_id
                        WHERE s.content LIKE ?
                        ORDER BY v.upload_date DESC, s.start_time ASC
                        LIMIT ?
                    """, (f'%{query}%', limit))
                    
                    for row in cursor.fetchall():
                        relevance_score = self._calculate_simple_relevance(query, row['title'], row['content'])
                        results.append({
                            'video_id': row['video_id'],
                            'title': row['title'],
                            'content': row['content'],
                            'url': row['url'],
                            'type': 'subtitle',
                            'timestamp': row['start_time'],
                            'upload_date': row['upload_date'],
                            'relevance_score': relevance_score
                        })
                except sqlite3.OperationalError:
                    # Subtitles table might not exist
                    pass
                    
        except Exception as e:
            logger.error(f"Error searching database {db_path}", error=str(e))
        
        return results
    
    def _calculate_simple_relevance(self, query: str, title: str, content: str) -> float:
        """Calculate simple relevance score"""
        query_words = query.lower().split()
        title_lower = title.lower()
        content_lower = content.lower()
        
        score = 0.0
        total_words = len(query_words)
        
        for word in query_words:
            if word in title_lower:
                score += 0.4  # Title matches are more important
            if word in content_lower:
                score += 0.2
        
        return min(1.0, score / total_words) if total_words > 0 else 0.0
    
    def set_qna_service(self, qna_service):
        """Set the QnA service for processing questions"""
        self.qna_service = qna_service
        logger.info("QnA service configured for Telegram handler")
    
    async def send_qna_response_to_telegram(self, chat_id: str, question: str, 
                                           answer: str, metadata: Dict[str, Any] = None):
        """Send QnA response from web interface to Telegram"""
        try:
            # Format response for Telegram
            formatted_response = self._format_qna_response(question, answer, metadata)
            
            # Send to Telegram
            await self.telegram_service.send_message_to_chat(
                chat_id=chat_id,
                message=formatted_response,
                message_type=MessageType.QNA_RESPONSE,
                parse_mode="HTML"
            )
            
            logger.info("QnA response sent from web to Telegram", chat_id=chat_id)
            
        except Exception as e:
            logger.error("Error sending QnA response to Telegram", 
                        chat_id=chat_id, error=str(e))
    
    def _format_qna_response(self, question: str, answer: str, 
                           metadata: Dict[str, Any] = None) -> str:
        """Format QnA response for Telegram display"""
        try:
            # Basic formatting
            formatted = f"<b>Q:</b> {question}\n\n<b>A:</b> {answer}"
            
            # Add metadata if available
            if metadata:
                if metadata.get("video_title"):
                    formatted += f"\n\n📺 <i>Related to: {metadata['video_title']}</i>"
                
                if metadata.get("channel_name"):
                    formatted += f"\n🎬 <i>Channel: {metadata['channel_name']}</i>"
                
                if metadata.get("confidence_score"):
                    confidence = metadata["confidence_score"]
                    if confidence < 0.7:
                        formatted += f"\n\n⚠️ <i>Note: This answer has moderate confidence ({confidence:.1%})</i>"
            
            return formatted
        
        except Exception as e:
            logger.error("Error formatting QnA response", error=str(e))
            return f"Q: {question}\n\nA: {answer}"
    
    async def handle_command(self, chat_id: str, command: str, args: str, 
                           message_data: Dict[str, Any]):
        """Handle Telegram commands (e.g., /help, /status)"""
        try:
            user_info = message_data.get("from", {})
            
            if command == "help":
                help_text = """
<b>Available Commands:</b>

• Ask any question about the videos
• Use /status to check system status
• Use /help to see this message

<b>Tips:</b>
• Be specific in your questions
• Reference video titles or topics
• Questions are automatically detected
                """.strip()
                
                await self.telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=help_text,
                    message_type=MessageType.SYSTEM_NOTIFICATION,
                    parse_mode="HTML"
                )
            
            elif command == "status":
                queue_status = self.telegram_service.get_queue_status()
                
                status_text = f"""
<b>System Status:</b>

• Service Running: {'✅' if queue_status['is_running'] else '❌'}
• Active Chats: {queue_status['active_chats']}
• Queue Length: {queue_status.get('persistent_queue_stats', {}).get('statistics', {}).get('pending', 0)}
• QnA Service: {'✅' if self.qna_service else '❌'}
                """.strip()
                
                await self.telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=status_text,
                    message_type=MessageType.SYSTEM_NOTIFICATION,
                    parse_mode="HTML"
                )
            
            else:
                await self.telegram_service.send_message_to_chat(
                    chat_id=chat_id,
                    message=f"Unknown command: /{command}. Use /help for available commands.",
                    message_type=MessageType.SYSTEM_NOTIFICATION
                )
            
            logger.info("Handled Telegram command", 
                       chat_id=chat_id, command=command, user_id=user_info.get("id"))
        
        except Exception as e:
            logger.error("Error handling Telegram command", 
                        chat_id=chat_id, command=command, error=str(e))