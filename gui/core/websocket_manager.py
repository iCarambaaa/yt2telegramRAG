"""
WebSocket Manager for real-time communication across all interfaces.

CRITICAL: Real-time synchronization backbone - failures affect user experience
FALLBACK: Graceful degradation to polling if WebSocket fails
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime
import asyncio

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections and real-time message broadcasting.
    
    CRITICAL: Core real-time communication system
    FALLBACK: Connection recovery and graceful degradation
    """
    
    def __init__(self):
        # Active connections by client_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Message queues for offline clients
        self.message_queues: Dict[str, List[Dict]] = {}
        
        # Connection groups for targeted broadcasting
        self.connection_groups: Dict[str, List[str]] = {}
    
    async def initialize(self):
        """Initialize WebSocket manager."""
        logger.info("Initializing WebSocket manager")
        # Initialize any required resources
        
    async def cleanup(self):
        """Cleanup WebSocket connections on shutdown."""
        logger.info("Cleaning up WebSocket connections")
        
        # Close all active connections
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.close()
                logger.info("Closed WebSocket connection", client_id=client_id)
            except Exception as e:
                logger.error("Error closing WebSocket", client_id=client_id, error=str(e))
        
        self.active_connections.clear()
        self.connection_metadata.clear()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accept new WebSocket connection.
        
        SECURITY: Validate client_id format
        """
        # SECURITY: Basic client_id validation
        if not client_id or len(client_id) > 100:
            await websocket.close(code=1008, reason="Invalid client ID")
            return
        
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Store connection metadata
        self.connection_metadata[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        
        # Send queued messages if any
        await self._send_queued_messages(client_id)
        
        # Notify other clients about new connection
        await self.broadcast_to_group("system", {
            "type": "client_connected",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_client=client_id)
        
        logger.info("WebSocket client connected", client_id=client_id)
    
    async def disconnect(self, client_id: str):
        """Handle client disconnection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]
        
        # Remove from all groups
        for group_name, members in self.connection_groups.items():
            if client_id in members:
                members.remove(client_id)
        
        # Notify other clients about disconnection
        await self.broadcast_to_group("system", {
            "type": "client_disconnected", 
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info("WebSocket client disconnected", client_id=client_id)
    
    async def handle_message(self, client_id: str, message: str):
        """
        Handle incoming message from client.
        
        SECURITY: Validate and sanitize incoming messages
        """
        try:
            # Update last activity
            if client_id in self.connection_metadata:
                self.connection_metadata[client_id]["last_activity"] = datetime.utcnow().isoformat()
                self.connection_metadata[client_id]["message_count"] += 1
            
            # Parse message
            data = json.loads(message)
            
            # SECURITY: Validate message structure
            if not isinstance(data, dict) or "type" not in data:
                await self.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid message format"
                })
                return
            
            message_type = data.get("type")
            
            # Handle different message types
            if message_type == "ping":
                await self.send_to_client(client_id, {"type": "pong"})
            
            elif message_type == "join_group":
                group_name = data.get("group")
                if group_name:
                    await self.add_to_group(client_id, group_name)
            
            elif message_type == "leave_group":
                group_name = data.get("group")
                if group_name:
                    await self.remove_from_group(client_id, group_name)
            
            elif message_type == "broadcast":
                # Broadcast message to all clients in same groups
                await self.broadcast_from_client(client_id, data.get("payload", {}))
            
            elif message_type == "qna_question":
                # Handle Q&A question
                await self.handle_qna_question(client_id, data.get("data", {}))
            
            elif message_type == "join_qna_room":
                # Join Q&A room for real-time updates
                channel = data.get("data", {}).get("channel", "all")
                room = f"qna_{channel}"
                await self.add_to_group(client_id, room)
                await self.send_to_client(client_id, {
                    "type": "qna_room_joined",
                    "data": {"room": room, "channel": channel}
                })
            
            else:
                logger.warning("Unknown message type", client_id=client_id, message_type=message_type)
        
        except json.JSONDecodeError:
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Invalid JSON format"
            })
        except Exception as e:
            logger.error("Error handling WebSocket message", client_id=client_id, error=str(e))
            await self.send_to_client(client_id, {
                "type": "error",
                "message": "Internal server error"
            })
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                logger.error("Failed to send message to client", client_id=client_id, error=str(e))
                # FALLBACK: Queue message for later delivery
                await self._queue_message(client_id, message)
                return False
        else:
            # FALLBACK: Queue message for offline client
            await self._queue_message(client_id, message)
            return False
    
    async def broadcast_to_all(self, message: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast message to all connected clients."""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            if exclude_client and client_id == exclude_client:
                continue
            
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error("Failed to broadcast to client", client_id=client_id, error=str(e))
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def broadcast_to_group(self, group_name: str, message: Dict[str, Any], exclude_client: Optional[str] = None):
        """Broadcast message to all clients in a specific group."""
        if group_name not in self.connection_groups:
            return
        
        disconnected_clients = []
        
        for client_id in self.connection_groups[group_name]:
            if exclude_client and client_id == exclude_client:
                continue
            
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error("Failed to broadcast to group member", client_id=client_id, group=group_name, error=str(e))
                    disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
    
    async def add_to_group(self, client_id: str, group_name: str):
        """Add client to a group for targeted broadcasting."""
        if group_name not in self.connection_groups:
            self.connection_groups[group_name] = []
        
        if client_id not in self.connection_groups[group_name]:
            self.connection_groups[group_name].append(client_id)
            
            await self.send_to_client(client_id, {
                "type": "group_joined",
                "group": group_name
            })
            
            logger.info("Client added to group", client_id=client_id, group=group_name)
    
    async def remove_from_group(self, client_id: str, group_name: str):
        """Remove client from a group."""
        if group_name in self.connection_groups and client_id in self.connection_groups[group_name]:
            self.connection_groups[group_name].remove(client_id)
            
            await self.send_to_client(client_id, {
                "type": "group_left",
                "group": group_name
            })
            
            logger.info("Client removed from group", client_id=client_id, group=group_name)
    
    async def broadcast_from_client(self, sender_id: str, payload: Dict[str, Any]):
        """Broadcast message from one client to others in same groups."""
        # Find all groups the sender belongs to
        sender_groups = [group for group, members in self.connection_groups.items() if sender_id in members]
        
        # Broadcast to all groups
        for group_name in sender_groups:
            await self.broadcast_to_group(group_name, {
                "type": "client_message",
                "sender": sender_id,
                "payload": payload,
                "timestamp": datetime.utcnow().isoformat()
            }, exclude_client=sender_id)
    
    async def broadcast_system_update(self, update_type: str, data: Dict[str, Any], 
                                    target_groups: Optional[List[str]] = None):
        """Broadcast system updates to specific groups or all clients."""
        message = {
            "type": "system_update",
            "update_type": update_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if target_groups:
            for group_name in target_groups:
                await self.broadcast_to_group(group_name, message)
        else:
            await self.broadcast_to_all(message)
    
    async def notify_message_update(self, message_data: Dict[str, Any]):
        """Notify clients about new or updated messages."""
        await self.broadcast_system_update("message_update", message_data, ["messages"])
    
    async def notify_channel_update(self, channel_data: Dict[str, Any]):
        """Notify clients about channel configuration changes."""
        await self.broadcast_system_update("channel_update", channel_data, ["channels"])
    
    async def notify_qna_update(self, qna_data: Dict[str, Any]):
        """Notify clients about QnA conversation updates."""
        await self.broadcast_system_update("qna_update", qna_data, ["qna"])
    
    async def notify_analytics_update(self, analytics_data: Dict[str, Any]):
        """Notify clients about analytics updates."""
        await self.broadcast_system_update("analytics_update", analytics_data, ["analytics"])
    
    async def _queue_message(self, client_id: str, message: Dict[str, Any]):
        """Queue message for offline client."""
        if client_id not in self.message_queues:
            self.message_queues[client_id] = []
        
        # Add timestamp to queued message
        message["queued_at"] = datetime.utcnow().isoformat()
        self.message_queues[client_id].append(message)
        
        # COST: Limit queue size to prevent memory issues
        max_queue_size = 100
        if len(self.message_queues[client_id]) > max_queue_size:
            self.message_queues[client_id] = self.message_queues[client_id][-max_queue_size:]
    
    async def _send_queued_messages(self, client_id: str):
        """Send all queued messages to newly connected client."""
        if client_id in self.message_queues:
            messages = self.message_queues[client_id]
            
            for message in messages:
                await self.send_to_client(client_id, message)
            
            # Clear queue after sending
            del self.message_queues[client_id]
            
            logger.info("Sent queued messages to client", client_id=client_id, count=len(messages))
    
    def get_status(self) -> Dict[str, Any]:
        """Get WebSocket manager status for health checks."""
        return {
            "active_connections": len(self.active_connections),
            "connection_groups": {group: len(members) for group, members in self.connection_groups.items()},
            "queued_messages": {client: len(messages) for client, messages in self.message_queues.items()},
            "status": "operational"
        }
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific client."""
        if client_id in self.connection_metadata:
            info = self.connection_metadata[client_id].copy()
            info["is_connected"] = client_id in self.active_connections
            info["groups"] = [group for group, members in self.connection_groups.items() if client_id in members]
            info["queued_messages"] = len(self.message_queues.get(client_id, []))
            return info
        return None
    
    async def handle_qna_question(self, client_id: str, question_data: Dict[str, Any]):
        """Handle Q&A question via WebSocket."""
        try:
            question = question_data.get("question", "")
            channel_context = question_data.get("channelContext")
            conversation_id = question_data.get("conversationId", f"conv_{int(datetime.utcnow().timestamp())}")
            
            if not question.strip():
                await self.send_to_client(client_id, {
                    "type": "qna_error",
                    "data": {"message": "Question cannot be empty"}
                })
                return
            
            # Send processing acknowledgment
            await self.send_to_client(client_id, {
                "type": "qna_processing",
                "data": {
                    "question": question,
                    "conversationId": conversation_id
                }
            })
            
            # Process question (this would integrate with the actual QnA service)
            response = await self._process_qna_question_ws(question, channel_context, conversation_id)
            
            # Send response
            await self.send_to_client(client_id, {
                "type": "qna_response",
                "data": response
            })
            
            # Broadcast activity to Q&A room
            room = f"qna_{channel_context or 'all'}"
            await self.broadcast_to_group(room, {
                "type": "qna_activity",
                "data": {
                    "question": question,
                    "channel": channel_context,
                    "timestamp": datetime.utcnow().isoformat(),
                    "user": client_id
                }
            }, exclude_client=client_id)
            
        except Exception as e:
            logger.error("Error handling Q&A question via WebSocket", client_id=client_id, error=str(e))
            await self.send_to_client(client_id, {
                "type": "qna_error",
                "data": {"message": "Failed to process question"}
            })
    
    async def _process_qna_question_ws(self, question: str, channel_context: Optional[str], 
                                      conversation_id: str) -> Dict[str, Any]:
        """Process Q&A question for WebSocket response."""
        try:
            # This would integrate with the actual Q&A processing logic
            # For now, simulate processing with a basic response
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Basic response structure
            response = {
                "id": f"qna_{int(datetime.utcnow().timestamp())}",
                "question": question,
                "answer": f"This is a WebSocket response to your question: '{question}'. The full Q&A integration is being implemented.",
                "timestamp": datetime.utcnow().isoformat(),
                "contextVideos": [
                    {
                        "id": "sample_video_1",
                        "title": "Sample Video Title",
                        "url": "https://youtube.com/watch?v=sample",
                        "relevanceScore": 0.8
                    }
                ],
                "channelContext": channel_context,
                "confidenceScore": 0.75,
                "followUpSuggestions": [
                    "Can you elaborate on this topic?",
                    "What are the practical applications?",
                    "Are there any related concepts?"
                ],
                "conversationId": conversation_id,
                "responseTime": 1.0
            }
            
            return response
            
        except Exception as e:
            logger.error("Error processing Q&A question", error=str(e))
            return {
                "id": f"error_{int(datetime.utcnow().timestamp())}",
                "question": question,
                "answer": "I encountered an error processing your question. Please try again.",
                "timestamp": datetime.utcnow().isoformat(),
                "contextVideos": [],
                "channelContext": channel_context,
                "confidenceScore": 0.0,
                "followUpSuggestions": [],
                "conversationId": conversation_id,
                "responseTime": 0.0
            }