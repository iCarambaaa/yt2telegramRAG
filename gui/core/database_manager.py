"""
Database Manager for unified GUI platform with multiple SQLite databases.
"""

import sqlite3
import asyncio
import aiosqlite
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class DatabaseManager:
    """Manages multiple SQLite database connections for the unified platform."""
    
    def __init__(self):
        self.connections: Dict[str, aiosqlite.Connection] = {}
        self.db_paths = {
            "gui_main": "gui/data/gui_main.db",
            "messages": "gui/data/messages.db", 
            "conversations": "gui/data/conversations.db",
            "analytics": "gui/data/analytics.db"
        }
        self.max_connections = 10
        self.connection_timeout = 30
        self.health_status = {}
    
    async def initialize(self):
        """Initialize database connections and create schemas."""
        logger.info("Initializing database manager")
        
        try:
            os.makedirs("gui/data", exist_ok=True)
            
            for db_name, db_path in self.db_paths.items():
                await self._initialize_database(db_name, db_path)
            
            logger.info("Database manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database manager", error=str(e))
            raise
    
    async def cleanup(self):
        """Close all database connections."""
        logger.info("Cleaning up database connections")
        
        for db_name, connection in self.connections.items():
            try:
                await connection.close()
                logger.info("Closed database connection", database=db_name)
            except Exception as e:
                logger.error("Error closing database connection", database=db_name, error=str(e))
        
        self.connections.clear()
    
    async def _initialize_database(self, db_name: str, db_path: str):
        """Initialize a specific database with schema."""
        try:
            connection = await aiosqlite.connect(
                db_path,
                timeout=self.connection_timeout,
                check_same_thread=False
            )
            
            await connection.execute("PRAGMA journal_mode=WAL")
            await connection.execute("PRAGMA synchronous=NORMAL")
            await connection.execute("PRAGMA cache_size=10000")
            await connection.execute("PRAGMA temp_store=memory")
            
            self.connections[db_name] = connection
            
            await self._create_schema(db_name, connection)
            
            self.health_status[db_name] = {
                "status": "healthy",
                "last_check": datetime.utcnow().isoformat(),
                "path": db_path
            }
            
            logger.info("Database initialized", database=db_name, path=db_path)
            
        except Exception as e:
            logger.error("Failed to initialize database", database=db_name, error=str(e))
            self.health_status[db_name] = {
                "status": "error",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
                "path": db_path
            }
            raise
    
    async def _create_schema(self, db_name: str, connection: aiosqlite.Connection):
        """Create database schema based on database type."""
        
        if db_name == "gui_main":
            await self._create_main_schema(connection)
        elif db_name == "messages":
            await self._create_messages_schema(connection)
        elif db_name == "conversations":
            await self._create_conversations_schema(connection)
        elif db_name == "analytics":
            await self._create_analytics_schema(connection)
    
    async def _create_main_schema(self, connection: aiosqlite.Connection):
        """Create main GUI database schema."""
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                interface_type TEXT CHECK(interface_type IN ('web', 'telegram', 'ai_chat')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context_data TEXT,
                preferences TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS interface_states (
                session_id TEXT PRIMARY KEY,
                active_interface TEXT,
                available_interfaces TEXT,
                current_task TEXT,
                context_data TEXT,
                sync_status TEXT,
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT
            )
        """)
        
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_config_key ON system_config(key)")
        
        await connection.commit()
    
    async def _create_messages_schema(self, connection: aiosqlite.Connection):
        """Create messages database schema for Telegram mirror."""
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS unified_messages (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                message_type TEXT CHECK(message_type IN ('telegram_out', 'telegram_in', 'web_out', 'qna_question', 'qna_answer')),
                channel_id TEXT,
                chat_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                thread_id TEXT,
                metadata TEXT,
                formatting TEXT,
                attachments TEXT,
                search_content TEXT
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS message_threads (
                thread_id TEXT PRIMARY KEY,
                channel_id TEXT,
                chat_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                participants TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_archived BOOLEAN DEFAULT 0
            )
        """)
        
        # Create FTS5 virtual table for full-text search
        await connection.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                id UNINDEXED,
                content,
                search_content,
                channel_id UNINDEXED,
                message_type UNINDEXED,
                content='unified_messages',
                content_rowid='rowid'
            )
        """)
        
        # Create triggers to keep FTS table in sync
        await connection.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_insert AFTER INSERT ON unified_messages BEGIN
                INSERT INTO messages_fts(id, content, search_content, channel_id, message_type)
                VALUES (new.id, new.content, new.search_content, new.channel_id, new.message_type);
            END
        """)
        
        await connection.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_delete AFTER DELETE ON unified_messages BEGIN
                DELETE FROM messages_fts WHERE id = old.id;
            END
        """)
        
        await connection.execute("""
            CREATE TRIGGER IF NOT EXISTS messages_fts_update AFTER UPDATE ON unified_messages BEGIN
                DELETE FROM messages_fts WHERE id = old.id;
                INSERT INTO messages_fts(id, content, search_content, channel_id, message_type)
                VALUES (new.id, new.content, new.search_content, new.channel_id, new.message_type);
            END
        """)
        
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON unified_messages(channel_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON unified_messages(chat_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON unified_messages(timestamp)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON unified_messages(message_type)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread ON unified_messages(thread_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_threads_channel ON message_threads(channel_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_threads_active ON message_threads(is_active)")
        
        await connection.commit()
    
    async def _create_conversations_schema(self, connection: aiosqlite.Connection):
        """Create conversations database schema for QnA system."""
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                interface_type TEXT CHECK(interface_type IN ('web', 'telegram', 'ai_chat')),
                channel_context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                preferences TEXT,
                conversation_history TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS qna_exchanges (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                context_videos TEXT,
                channel_context TEXT,
                interface_source TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence_score REAL,
                follow_up_suggestions TEXT,
                feedback_rating INTEGER,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id)
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS video_contexts (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT,
                title TEXT,
                summary TEXT,
                transcript_chunks TEXT,
                embeddings BLOB,
                metadata TEXT,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversation_sessions(user_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversation_sessions(is_active)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_qna_session ON qna_exchanges(session_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_qna_timestamp ON qna_exchanges(timestamp)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_video_channel ON video_contexts(channel_id)")
        
        await connection.commit()
    
    async def _create_analytics_schema(self, connection: aiosqlite.Connection):
        """Create analytics database schema."""
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metric_unit TEXT,
                tags TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT,
                activity_type TEXT,
                interface_type TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await connection.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT,
                method TEXT,
                response_time_ms INTEGER,
                status_code INTEGER,
                user_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity(timestamp)")
        await connection.execute("CREATE INDEX IF NOT EXISTS idx_performance_endpoint ON performance_metrics(endpoint)")
        
        await connection.commit()
    
    async def get_connection(self, db_name: str) -> aiosqlite.Connection:
        """Get database connection by name."""
        if db_name not in self.connections:
            raise ValueError(f"Database '{db_name}' not initialized")
        
        return self.connections[db_name]
    
    async def execute_query(self, db_name: str, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        try:
            connection = await self.get_connection(db_name)
            
            if params:
                cursor = await connection.execute(query, params)
            else:
                cursor = await connection.execute(query)
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]
            
            await cursor.close()
            return results
            
        except Exception as e:
            logger.error("Database query failed", database=db_name, query=query[:100], error=str(e))
            raise
    
    async def execute_update(self, db_name: str, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        try:
            connection = await self.get_connection(db_name)
            
            if params:
                cursor = await connection.execute(query, params)
            else:
                cursor = await connection.execute(query)
            
            affected_rows = cursor.rowcount
            await connection.commit()
            await cursor.close()
            
            return affected_rows
            
        except Exception as e:
            logger.error("Database update failed", database=db_name, query=query[:100], error=str(e))
            await connection.rollback()
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all databases."""
        health_results = {}
        
        for db_name in self.db_paths.keys():
            try:
                result = await self.execute_query(db_name, "SELECT 1 as test")
                
                if result and result[0]["test"] == 1:
                    health_results[db_name] = {
                        "status": "healthy",
                        "last_check": datetime.utcnow().isoformat()
                    }
                else:
                    health_results[db_name] = {
                        "status": "error",
                        "error": "Invalid query result",
                        "last_check": datetime.utcnow().isoformat()
                    }
                    
            except Exception as e:
                health_results[db_name] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
        
        self.health_status.update(health_results)
        
        return {
            "overall_status": "healthy" if all(db["status"] == "healthy" for db in health_results.values()) else "degraded",
            "databases": health_results
        }
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics for all databases."""
        stats = {}
        
        for db_name in self.db_paths.keys():
            try:
                tables_info = await self.execute_query(
                    db_name,
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                
                table_stats = {}
                for table in tables_info:
                    table_name = table["name"]
                    count_result = await self.execute_query(
                        db_name,
                        f"SELECT COUNT(*) as count FROM {table_name}"
                    )
                    table_stats[table_name] = count_result[0]["count"] if count_result else 0
                
                stats[db_name] = {
                    "tables": table_stats,
                    "total_tables": len(tables_info),
                    "path": self.db_paths[db_name]
                }
                
            except Exception as e:
                logger.error("Failed to get database stats", database=db_name, error=str(e))
                stats[db_name] = {"error": str(e)}
        
        return stats