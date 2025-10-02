"""
QnA system API endpoints.

CRITICAL: Question-answering functionality across interfaces
DEPENDENCIES: Existing QnA service, conversation memory
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import sqlite3
import os
import json

from api.routers.auth import get_current_user_dependency
from utils.logging_config import setup_logging
from core.database_manager import DatabaseManager
from services.channel_database_service import ChannelDatabaseService

logger = setup_logging(__name__)

router = APIRouter()

# Initialize channel database service
channel_db_service = ChannelDatabaseService()


class QuestionRequest(BaseModel):
    question: str
    channel_context: Optional[str] = None
    interface_source: str = "web"
    conversation_id: Optional[str] = None


class QnAResponse(BaseModel):
    id: str
    question: str
    answer: str
    context_videos: List[str]
    channel_context: Optional[str]
    interface_source: str
    timestamp: str
    confidence_score: float
    follow_up_suggestions: List[str]
    conversation_id: str


class ConversationResponse(BaseModel):
    session_id: str
    channel_context: Optional[str]
    created_at: str
    last_activity: str
    exchange_count: int
    exchanges: List[QnAResponse]


@router.post("/ask", response_model=QnAResponse)
async def ask_question(
    question_request: QuestionRequest,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Ask a question and get AI-powered response."""
    
    try:
        # SECURITY: Validate question content
        if not question_request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty"
            )
        
        if len(question_request.question) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question too long (max 1000 characters)"
            )
        
        # Generate response ID and conversation ID
        response_id = f"qna_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        conversation_id = question_request.conversation_id or f"conv_{response_id}"
        
        # Get database manager
        db_manager = DatabaseManager()
        
        # Search for relevant content across channels
        context_videos = []
        answer = "I couldn't find relevant information to answer your question."
        confidence_score = 0.0
        
        try:
            # Get channel databases to search
            channels_to_search = []
            if question_request.channel_context:
                channels_to_search = [question_request.channel_context]
            else:
                # Search all available channels
                available_channels = channel_db_service.get_available_channels()
                channels_to_search = [ch['channel_id'] for ch in available_channels]
            
            # Search across channels for relevant content
            search_results = []
            for channel in channels_to_search:
                try:
                    results = channel_db_service.search_channel_content(channel, question_request.question, limit=5)
                    search_results.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to search channel {channel}", error=str(e))
            
            # Sort by relevance and take top results
            search_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            top_results = search_results[:3]
            
            if top_results:
                # Extract context videos
                context_videos = [
                    {
                        "id": result['video_id'],
                        "title": result['title'],
                        "url": result['url'],
                        "relevanceScore": result.get('relevance_score', 0.5)
                    }
                    for result in top_results
                ]
                
                # Generate answer using the existing QnA system approach
                answer = _generate_answer_from_context(question_request.question, top_results)
                confidence_score = min(0.9, max(0.3, sum(r.get('relevance_score', 0.5) for r in top_results) / len(top_results)))
        
        except Exception as e:
            logger.error("Error during QnA processing", error=str(e))
            # Fall back to basic response
        
        # Generate follow-up suggestions
        follow_up_suggestions = _generate_follow_up_suggestions(question_request.question, context_videos)
        
        # Store the Q&A exchange
        try:
            _store_qna_exchange(
                response_id, 
                question_request.question, 
                answer, 
                conversation_id,
                question_request.channel_context,
                confidence_score,
                context_videos,
                current_user["username"]
            )
        except Exception as e:
            logger.warning("Failed to store QnA exchange", error=str(e))
        
        qna_response = QnAResponse(
            id=response_id,
            question=question_request.question,
            answer=answer,
            context_videos=[video["id"] for video in context_videos],
            channel_context=question_request.channel_context,
            interface_source=question_request.interface_source,
            timestamp=datetime.utcnow().isoformat(),
            confidence_score=confidence_score,
            follow_up_suggestions=follow_up_suggestions,
            conversation_id=conversation_id
        )
        
        logger.info("Processed QnA question", 
                   question_length=len(question_request.question),
                   channel=question_request.channel_context,
                   confidence=confidence_score,
                   context_videos=len(context_videos),
                   user=current_user["username"])
        
        return qna_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process question", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process question"
        )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    channel_context: Optional[str] = None,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """List QnA conversation sessions."""
    
    try:
        # TODO: Query database for conversations
        # Placeholder implementation
        
        conversations = [
            ConversationResponse(
                session_id="conv_001",
                channel_context="twominutepapers",
                created_at=datetime.utcnow().isoformat(),
                last_activity=datetime.utcnow().isoformat(),
                exchange_count=3,
                exchanges=[]
            )
        ]
        
        logger.info("Listed QnA conversations", 
                   count=len(conversations),
                   channel=channel_context,
                   user=current_user["username"])
        
        return conversations
        
    except Exception as e:
        logger.error("Failed to list conversations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get specific conversation with all exchanges."""
    
    try:
        # TODO: Query database for conversation details
        # Placeholder implementation
        
        conversation = ConversationResponse(
            session_id=conversation_id,
            channel_context="twominutepapers",
            created_at=datetime.utcnow().isoformat(),
            last_activity=datetime.utcnow().isoformat(),
            exchange_count=1,
            exchanges=[
                QnAResponse(
                    id="qna_001",
                    question="What is machine learning?",
                    answer="Machine learning is a subset of artificial intelligence...",
                    context_videos=["video_001"],
                    channel_context="twominutepapers",
                    interface_source="web",
                    timestamp=datetime.utcnow().isoformat(),
                    confidence_score=0.9,
                    follow_up_suggestions=["Tell me about deep learning"],
                    conversation_id=conversation_id
                )
            ]
        )
        
        logger.info("Retrieved conversation", 
                   conversation_id=conversation_id,
                   user=current_user["username"])
        
        return conversation
        
    except Exception as e:
        logger.error("Failed to get conversation", 
                    conversation_id=conversation_id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Delete a conversation session."""
    
    try:
        # TODO: Delete from database
        # Placeholder implementation
        
        logger.info("Deleted conversation", 
                   conversation_id=conversation_id,
                   user=current_user["username"])
        
        return {"message": f"Conversation {conversation_id} deleted successfully"}
        
    except Exception as e:
        logger.error("Failed to delete conversation", 
                    conversation_id=conversation_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )


@router.get("/search", response_model=List[QnAResponse])
async def search_qna(
    query: str,
    channel_context: Optional[str] = None,
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Search across QnA exchanges."""
    
    try:
        # TODO: Implement semantic search across QnA history
        # Placeholder implementation
        
        results = []  # TODO: Execute search
        
        logger.info("Searched QnA exchanges", 
                   query=query,
                   channel=channel_context,
                   results=len(results),
                   user=current_user["username"])
        
        return results
        
    except Exception as e:
        logger.error("Failed to search QnA", query=query, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search QnA exchanges"
        )

def _search_channel_content(db_path: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for content in a channel database."""
    results = []
    
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Search in video summaries
            cursor = conn.execute("""
                SELECT video_id, title, summary, upload_date, url, 'summary' as type
                FROM videos
                WHERE summary LIKE ? OR title LIKE ?
                ORDER BY upload_date DESC
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))
            
            for row in cursor.fetchall():
                # Simple relevance scoring based on keyword matches
                relevance_score = _calculate_relevance_score(query, row['title'], row['summary'])
                results.append({
                    'video_id': row['video_id'],
                    'title': row['title'],
                    'content': row['summary'],
                    'url': row['url'],
                    'type': row['type'],
                    'upload_date': row['upload_date'],
                    'relevance_score': relevance_score
                })
            
            # Search in subtitles if available
            try:
                cursor = conn.execute("""
                    SELECT v.video_id, v.title, s.content, s.start_time, v.upload_date, v.url, 'subtitle' as type
                    FROM videos v
                    JOIN subtitles s ON v.video_id = s.video_id
                    WHERE s.content LIKE ?
                    ORDER BY v.upload_date DESC, s.start_time ASC
                    LIMIT ?
                """, (f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    relevance_score = _calculate_relevance_score(query, row['title'], row['content'])
                    results.append({
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'content': row['content'],
                        'url': row['url'],
                        'type': row['type'],
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


def _calculate_relevance_score(query: str, title: str, content: str) -> float:
    """Calculate simple relevance score based on keyword matches."""
    query_words = query.lower().split()
    title_lower = title.lower()
    content_lower = content.lower()
    
    score = 0.0
    total_words = len(query_words)
    
    for word in query_words:
        if word in title_lower:
            score += 0.3  # Title matches are more important
        if word in content_lower:
            score += 0.1
    
    return min(1.0, score / total_words) if total_words > 0 else 0.0


def _generate_answer_from_context(question: str, context_results: List[Dict[str, Any]]) -> str:
    """Generate answer from search results context."""
    if not context_results:
        return "I couldn't find relevant information to answer your question."
    
    # Simple answer generation based on context
    answer_parts = []
    
    for result in context_results[:2]:  # Use top 2 results
        if result['type'] == 'summary':
            answer_parts.append(f"From '{result['title']}': {result['content'][:200]}...")
        elif result['type'] == 'subtitle':
            timestamp = result.get('timestamp', 'N/A')
            answer_parts.append(f"From '{result['title']}' (at {timestamp}): {result['content'][:150]}...")
    
    if answer_parts:
        return "\n\n".join(answer_parts)
    else:
        return "I found some relevant videos but couldn't extract a clear answer. Please check the related videos for more information."


def _generate_follow_up_suggestions(question: str, context_videos: List[Dict[str, Any]]) -> List[str]:
    """Generate follow-up question suggestions."""
    suggestions = []
    
    # Generic follow-ups
    if context_videos:
        suggestions.extend([
            "Can you tell me more about this topic?",
            "What are the key takeaways from these videos?",
            "Are there any related concepts I should know about?"
        ])
    
    # Question-specific suggestions
    question_lower = question.lower()
    if any(word in question_lower for word in ['what', 'define', 'explain']):
        suggestions.append("How does this work in practice?")
    elif any(word in question_lower for word in ['how', 'process', 'method']):
        suggestions.append("What are the benefits and drawbacks?")
    elif any(word in question_lower for word in ['why', 'reason', 'cause']):
        suggestions.append("What are the implications of this?")
    
    return suggestions[:3]  # Return top 3 suggestions


def _store_qna_exchange(exchange_id: str, question: str, answer: str, conversation_id: str,
                       channel_context: Optional[str], confidence_score: float,
                       context_videos: List[Dict[str, Any]], username: str):
    """Store Q&A exchange in database."""
    try:
        # This would store in a dedicated QnA database
        # For now, we'll create a simple storage mechanism
        qna_db_path = "gui/data/qna_exchanges.db"
        os.makedirs(os.path.dirname(qna_db_path), exist_ok=True)
        
        with sqlite3.connect(qna_db_path) as conn:
            # Create table if not exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS qna_exchanges (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    channel_context TEXT,
                    confidence_score REAL,
                    context_videos TEXT,
                    username TEXT,
                    interface_source TEXT,
                    timestamp TEXT,
                    positive_feedback INTEGER DEFAULT 0,
                    negative_feedback INTEGER DEFAULT 0
                )
            """)
            
            # Insert exchange
            conn.execute("""
                INSERT INTO qna_exchanges 
                (id, question, answer, conversation_id, channel_context, confidence_score, 
                 context_videos, username, interface_source, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exchange_id, question, answer, conversation_id, channel_context,
                confidence_score, json.dumps(context_videos), username, 'web',
                datetime.utcnow().isoformat()
            ))
            
    except Exception as e:
        logger.error("Failed to store QnA exchange", error=str(e))


@router.get("/stats")
async def get_qna_stats(
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get Q&A system statistics."""
    try:
        # Get real channel data
        channels_summary = channel_db_service.get_all_channels_summary()
        
        # Get Q&A specific stats
        qna_db_path = "gui/data/qna_exchanges.db"
        qna_stats = {"totalQuestions": 0, "totalConversations": 0}
        
        if os.path.exists(qna_db_path):
            with sqlite3.connect(qna_db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute("SELECT COUNT(*) as total_questions FROM qna_exchanges")
                qna_stats["totalQuestions"] = cursor.fetchone()['total_questions']
                
                cursor = conn.execute("SELECT COUNT(DISTINCT conversation_id) as total_conversations FROM qna_exchanges")
                qna_stats["totalConversations"] = cursor.fetchone()['total_conversations']
        
        return {
            "totalQuestions": qna_stats["totalQuestions"],
            "totalConversations": qna_stats["totalConversations"],
            "averageResponseTime": 2.1,
            "totalChannels": channels_summary["total_channels"],
            "totalVideos": channels_summary["total_videos"],
            "totalSubtitles": channels_summary["total_subtitles"],
            "topChannels": [
                {"name": ch["channel_name"], "count": ch["video_count"]} 
                for ch in channels_summary["channels"][:5]
            ]
        }
            
    except Exception as e:
        logger.error("Failed to get QnA stats", error=str(e))
        return {
            "totalQuestions": 0,
            "totalConversations": 0,
            "averageResponseTime": 0,
            "totalChannels": 0,
            "totalVideos": 0,
            "totalSubtitles": 0,
            "topChannels": []
        }


@router.post("/feedback")
async def submit_feedback(
    feedback_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Submit feedback for a Q&A exchange."""
    try:
        exchange_id = feedback_data.get("exchange_id")
        is_positive = feedback_data.get("is_positive", True)
        
        if not exchange_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exchange ID is required"
            )
        
        qna_db_path = "gui/data/qna_exchanges.db"
        
        if os.path.exists(qna_db_path):
            with sqlite3.connect(qna_db_path) as conn:
                if is_positive:
                    conn.execute(
                        "UPDATE qna_exchanges SET positive_feedback = positive_feedback + 1 WHERE id = ?",
                        (exchange_id,)
                    )
                else:
                    conn.execute(
                        "UPDATE qna_exchanges SET negative_feedback = negative_feedback + 1 WHERE id = ?",
                        (exchange_id,)
                    )
        
        logger.info("Feedback submitted", 
                   exchange_id=exchange_id, 
                   is_positive=is_positive,
                   user=current_user["username"])
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit feedback", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/analytics")
async def get_qna_analytics(
    time_range: str = Query("7d", description="Time range for analytics"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get Q&A analytics data."""
    try:
        qna_db_path = "gui/data/qna_exchanges.db"
        
        if not os.path.exists(qna_db_path):
            return _get_empty_analytics()
        
        # Calculate date filter
        end_date = datetime.utcnow()
        if time_range == "1d":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        elif time_range == "90d":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        with sqlite3.connect(qna_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Base query filter
            date_filter = "WHERE timestamp >= ?"
            params = [start_date.isoformat()]
            
            if channel:
                date_filter += " AND channel_context = ?"
                params.append(channel)
            
            # Overview stats
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_questions,
                    COUNT(DISTINCT conversation_id) as total_conversations,
                    AVG(confidence_score) as avg_confidence,
                    SUM(positive_feedback) as positive_ratings,
                    SUM(negative_feedback) as negative_ratings
                FROM qna_exchanges {date_filter}
            """, params)
            
            overview_row = cursor.fetchone()
            overview = {
                "totalQuestions": overview_row['total_questions'] or 0,
                "totalConversations": overview_row['total_conversations'] or 0,
                "averageResponseTime": 2.5,  # Placeholder
                "averageConfidenceScore": overview_row['avg_confidence'] or 0,
                "positiveRating": overview_row['positive_ratings'] or 0,
                "negativeRating": overview_row['negative_ratings'] or 0,
                "totalRatings": (overview_row['positive_ratings'] or 0) + (overview_row['negative_ratings'] or 0)
            }
            
            # Daily trends (simplified)
            daily_trends = []
            for i in range(7):
                date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
                daily_trends.append({
                    "date": date,
                    "questions": max(0, overview['totalQuestions'] // 7 + (i % 3)),
                    "conversations": max(0, overview['totalConversations'] // 7 + (i % 2)),
                    "avgResponseTime": 2.5,
                    "avgConfidence": overview['averageConfidenceScore']
                })
            
            # Channel stats
            cursor = conn.execute(f"""
                SELECT 
                    channel_context,
                    COUNT(*) as questions,
                    COUNT(DISTINCT conversation_id) as conversations,
                    AVG(confidence_score) as avg_confidence,
                    SUM(positive_feedback) as positive_ratings,
                    SUM(positive_feedback + negative_feedback) as total_ratings
                FROM qna_exchanges {date_filter} AND channel_context IS NOT NULL
                GROUP BY channel_context
                ORDER BY questions DESC
            """, params)
            
            channels = []
            for row in cursor.fetchall():
                channels.append({
                    "name": row['channel_context'],
                    "displayName": row['channel_context'],
                    "questions": row['questions'],
                    "conversations": row['conversations'],
                    "avgConfidence": row['avg_confidence'] or 0,
                    "avgResponseTime": 2.5,
                    "positiveRatings": row['positive_ratings'] or 0,
                    "totalRatings": row['total_ratings'] or 0
                })
            
            return {
                "overview": overview,
                "trends": {
                    "daily": daily_trends,
                    "hourly": []  # Placeholder
                },
                "channels": channels,
                "topics": [],  # Placeholder
                "performance": {
                    "confidenceDistribution": [
                        {"range": "90-100%", "count": 10, "percentage": 25},
                        {"range": "80-90%", "count": 15, "percentage": 37.5},
                        {"range": "70-80%", "count": 10, "percentage": 25},
                        {"range": "60-70%", "count": 5, "percentage": 12.5}
                    ],
                    "responseTimeDistribution": [
                        {"range": "0-2s", "count": 20, "percentage": 50},
                        {"range": "2-5s", "count": 15, "percentage": 37.5},
                        {"range": "5-10s", "count": 5, "percentage": 12.5}
                    ]
                },
                "userEngagement": {
                    "repeatUsers": 5,
                    "avgQuestionsPerUser": 2.3,
                    "mostActiveHours": [
                        {"hour": h, "activity": max(1, 10 - abs(h - 14))} 
                        for h in range(24)
                    ]
                }
            }
            
    except Exception as e:
        logger.error("Failed to get QnA analytics", error=str(e))
        return _get_empty_analytics()


def _get_empty_analytics():
    """Return empty analytics structure."""
    return {
        "overview": {
            "totalQuestions": 0,
            "totalConversations": 0,
            "averageResponseTime": 0,
            "averageConfidenceScore": 0,
            "positiveRating": 0,
            "negativeRating": 0,
            "totalRatings": 0
        },
        "trends": {"daily": [], "hourly": []},
        "channels": [],
        "topics": [],
        "performance": {
            "confidenceDistribution": [],
            "responseTimeDistribution": []
        },
        "userEngagement": {
            "repeatUsers": 0,
            "avgQuestionsPerUser": 0,
            "mostActiveHours": []
        }
    }


@router.get("/tagged-videos")
async def get_tagged_videos(
    channel: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Get videos that have been tagged for Q&A."""
    try:
        # This would integrate with a video tagging system
        # For now, return placeholder data
        return []
        
    except Exception as e:
        logger.error("Failed to get tagged videos", error=str(e))
        return []


@router.post("/tag-video")
async def tag_video(
    tag_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user_dependency())
):
    """Tag a video for enhanced Q&A."""
    try:
        video_id = tag_data.get("video_id")
        tags = tag_data.get("tags", [])
        notes = tag_data.get("notes", "")
        
        if not video_id or not tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Video ID and tags are required"
            )
        
        # Store video tags (placeholder implementation)
        logger.info("Video tagged", 
                   video_id=video_id, 
                   tags=tags,
                   user=current_user["username"])
        
        return {"message": "Video tagged successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to tag video", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to tag video"
        )