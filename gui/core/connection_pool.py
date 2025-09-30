"""
Enhanced database connection pool manager for multiple SQLite databases.

CRITICAL: Database connection management and performance optimization
FALLBACK: Connection recovery and graceful degradation
"""

import asyncio
import aiosqlite
from typing import Dict, List, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import logging
from pathlib import Path

from utils.logging_config import setup_logging

logger = setup_logging(__name__)


class ConnectionPool:
    """
    Manages a pool of database connections for a single database.
    
    CRITICAL: Connection lifecycle management
    COST: Efficient resource utilization
    """
    
    def __init__(self, db_path: str, max_connections: int = 10, 
                 connection_timeout: int = 30):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Connection pool
        self.available_connections: asyncio.Queue = asyncio.Queue(maxsize=max_connections)
        self.active_connections: Dict[str, aiosqlite.Connection] = {}
        self.connection_stats = {
            "created": 0,
            "active": 0,
            "total_requests": 0,
            "failed_requests": 0
        }
        
        # Health monitoring
        self.last_health_check = None
        self.health_status = "unknown"
    
    async def initialize(self):
        """Initialize the connection pool."""
        logger.info("Initializing connection pool", db_path=self.db_path)
        
        # Create initial connections
        initial_connections = min(3, self.max_connections)  # Start with 3 connections
        
        for i in range(initial_connections):
            try:
                connection = await self._create_connection()
                await self.available_connections.put(connection)
                self.connection_stats["created"] += 1
                
            except Exception as e:
                logger.error("Failed to create initial connection", 
                           db_path=self.db_path, error=str(e))
                raise
        
        logger.info("Connection pool initialized", 
                   db_path=self.db_path, 
                   initial_connections=initial_connections)
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection with optimized settings."""
        connection = await aiosqlite.connect(
            self.db_path,
            timeout=self.connection_timeout,
            check_same_thread=False
        )
        
        # Optimize connection settings
        await connection.execute("PRAGMA journal_mode=WAL")
        await connection.execute("PRAGMA synchronous=NORMAL")
        await connection.execute("PRAGMA cache_size=10000")
        await connection.execute("PRAGMA temp_store=memory")
        await connection.execute("PRAGMA mmap_size=268435456")  # 256MB
        await connection.execute("PRAGMA optimize")
        
        return connection
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """Get a connection from the pool."""
        connection = None
        connection_id = None
        
        try:
            self.connection_stats["total_requests"] += 1
            
            # Try to get available connection
            try:
                connection = await asyncio.wait_for(
                    self.available_connections.get(), 
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                # Create new connection if pool is empty and under limit
                if len(self.active_connections) < self.max_connections:
                    connection = await self._create_connection()
                    self.connection_stats["created"] += 1
                else:
                    raise Exception("Connection pool exhausted")
            
            # Track active connection
            connection_id = f"conn_{id(connection)}"
            self.active_connections[connection_id] = connection
            self.connection_stats["active"] += 1
            
            yield connection
            
        except Exception as e:
            self.connection_stats["failed_requests"] += 1
            logger.error("Connection pool error", db_path=self.db_path, error=str(e))
            raise
            
        finally:
            # Return connection to pool
            if connection and connection_id:
                try:
                    # Remove from active connections
                    if connection_id in self.active_connections:
                        del self.active_connections[connection_id]
                        self.connection_stats["active"] -= 1
                    
                    # Check if connection is still valid
                    await connection.execute("SELECT 1")
                    
                    # Return to pool if not full
                    if self.available_connections.qsize() < self.max_connections:
                        await self.available_connections.put(connection)
                    else:
                        await connection.close()
                        
                except Exception as e:
                    logger.warning("Failed to return connection to pool", 
                                 db_path=self.db_path, error=str(e))
                    try:
                        await connection.close()
                    except:
                        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the connection pool."""
        try:
            async with self.get_connection() as connection:
                await connection.execute("SELECT 1")
                
            self.health_status = "healthy"
            self.last_health_check = datetime.utcnow()
            
            return {
                "status": "healthy",
                "available_connections": self.available_connections.qsize(),
                "active_connections": len(self.active_connections),
                "stats": self.connection_stats.copy(),
                "last_check": self.last_health_check.isoformat()
            }
            
        except Exception as e:
            self.health_status = "unhealthy"
            self.last_health_check = datetime.utcnow()
            
            logger.error("Connection pool health check failed", 
                        db_path=self.db_path, error=str(e))
            
            return {
                "status": "unhealthy",
                "error": str(e),
                "available_connections": self.available_connections.qsize(),
                "active_connections": len(self.active_connections),
                "stats": self.connection_stats.copy(),
                "last_check": self.last_health_check.isoformat()
            }
    
    async def cleanup(self):
        """Clean up all connections in the pool."""
        logger.info("Cleaning up connection pool", db_path=self.db_path)
        
        # Close active connections
        for connection_id, connection in list(self.active_connections.items()):
            try:
                await connection.close()
                del self.active_connections[connection_id]
            except Exception as e:
                logger.error("Failed to close active connection", 
                           connection_id=connection_id, error=str(e))
        
        # Close available connections
        while not self.available_connections.empty():
            try:
                connection = await self.available_connections.get()
                await connection.close()
            except Exception as e:
                logger.error("Failed to close available connection", error=str(e))
        
        logger.info("Connection pool cleaned up", db_path=self.db_path)


class EnhancedDatabaseManager:
    """
    Enhanced database manager with connection pooling and advanced features.
    
    CRITICAL: Multi-database coordination with connection pooling
    FALLBACK: Graceful degradation and connection recovery
    """
    
    def __init__(self):
        # Connection pools for each database
        self.connection_pools: Dict[str, ConnectionPool] = {}
        
        # Database configurations
        self.db_configs = {
            "gui_main": {
                "path": "gui/data/gui_main.db",
                "max_connections": 5,
                "description": "Main GUI application database"
            },
            "messages": {
                "path": "gui/data/messages.db", 
                "max_connections": 8,
                "description": "Message mirror and Telegram integration"
            },
            "conversations": {
                "path": "gui/data/conversations.db",
                "max_connections": 6,
                "description": "QnA conversations and RAG data"
            },
            "analytics": {
                "path": "gui/data/analytics.db",
                "max_connections": 4,
                "description": "Analytics and performance metrics"
            }
        }
        
        # Global statistics
        self.global_stats = {
            "initialized_at": None,
            "total_queries": 0,
            "failed_queries": 0,
            "average_response_time": 0.0
        }
    
    async def initialize(self):
        """Initialize all database connection pools."""
        logger.info("Initializing enhanced database manager")
        
        try:
            # Ensure data directory exists
            Path("gui/data").mkdir(parents=True, exist_ok=True)
            
            # Initialize connection pools
            for db_name, config in self.db_configs.items():
                pool = ConnectionPool(
                    db_path=config["path"],
                    max_connections=config["max_connections"]
                )
                
                await pool.initialize()
                self.connection_pools[db_name] = pool
                
                logger.info("Database pool initialized", 
                           database=db_name, 
                           path=config["path"])
            
            # Create database schemas
            await self._create_all_schemas()
            
            self.global_stats["initialized_at"] = datetime.utcnow()
            logger.info("Enhanced database manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize enhanced database manager", error=str(e))
            raise
    
    async def _create_all_schemas(self):
        """Create schemas for all databases."""
        from core.database_manager import DatabaseManager
        
        # Use the existing schema creation logic
        temp_manager = DatabaseManager()
        
        for db_name, pool in self.connection_pools.items():
            async with pool.get_connection() as connection:
                await temp_manager._create_schema(db_name, connection)
    
    @asynccontextmanager
    async def get_connection(self, db_name: str) -> AsyncContextManager[aiosqlite.Connection]:
        """Get a connection for a specific database."""
        if db_name not in self.connection_pools:
            raise ValueError(f"Database '{db_name}' not configured")
        
        pool = self.connection_pools[db_name]
        async with pool.get_connection() as connection:
            yield connection
    
    async def execute_query(self, db_name: str, query: str, 
                          params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query with connection pooling."""
        start_time = datetime.utcnow()
        
        try:
            async with self.get_connection(db_name) as connection:
                if params:
                    cursor = await connection.execute(query, params)
                else:
                    cursor = await connection.execute(query)
                
                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                results = [dict(zip(columns, row)) for row in rows]
                
                await cursor.close()
                
                # Update statistics
                self.global_stats["total_queries"] += 1
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._update_average_response_time(response_time)
                
                return results
                
        except Exception as e:
            self.global_stats["failed_queries"] += 1
            logger.error("Enhanced database query failed", 
                        database=db_name, 
                        query=query[:100], 
                        error=str(e))
            raise
    
    async def execute_update(self, db_name: str, query: str, 
                           params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query with connection pooling."""
        start_time = datetime.utcnow()
        
        try:
            async with self.get_connection(db_name) as connection:
                if params:
                    cursor = await connection.execute(query, params)
                else:
                    cursor = await connection.execute(query)
                
                affected_rows = cursor.rowcount
                await connection.commit()
                await cursor.close()
                
                # Update statistics
                self.global_stats["total_queries"] += 1
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self._update_average_response_time(response_time)
                
                return affected_rows
                
        except Exception as e:
            self.global_stats["failed_queries"] += 1
            logger.error("Enhanced database update failed", 
                        database=db_name, 
                        query=query[:100], 
                        error=str(e))
            raise
    
    def _update_average_response_time(self, response_time_ms: float):
        """Update rolling average response time."""
        current_avg = self.global_stats["average_response_time"]
        total_queries = self.global_stats["total_queries"]
        
        # Simple rolling average
        self.global_stats["average_response_time"] = (
            (current_avg * (total_queries - 1) + response_time_ms) / total_queries
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for all database pools."""
        health_results = {}
        
        for db_name, pool in self.connection_pools.items():
            health_results[db_name] = await pool.health_check()
        
        # Overall health status
        all_healthy = all(
            result["status"] == "healthy" 
            for result in health_results.values()
        )
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "databases": health_results,
            "global_stats": self.global_stats.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def cleanup(self):
        """Clean up all connection pools."""
        logger.info("Cleaning up enhanced database manager")
        
        for db_name, pool in self.connection_pools.items():
            try:
                await pool.cleanup()
            except Exception as e:
                logger.error("Failed to cleanup database pool", 
                           database=db_name, error=str(e))
        
        self.connection_pools.clear()
        logger.info("Enhanced database manager cleaned up")
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        stats = {
            "global_stats": self.global_stats.copy(),
            "databases": {}
        }
        
        for db_name, pool in self.connection_pools.items():
            try:
                # Get pool statistics
                pool_health = await pool.health_check()
                
                # Get table statistics
                table_stats = {}
                async with self.get_connection(db_name) as connection:
                    cursor = await connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = await cursor.fetchall()
                    await cursor.close()
                    
                    for (table_name,) in tables:
                        cursor = await connection.execute(f"SELECT COUNT(*) FROM {table_name}")
                        count_result = await cursor.fetchone()
                        await cursor.close()
                        table_stats[table_name] = count_result[0] if count_result else 0
                
                stats["databases"][db_name] = {
                    "config": self.db_configs[db_name],
                    "pool_health": pool_health,
                    "table_stats": table_stats
                }
                
            except Exception as e:
                logger.error("Failed to get database stats", database=db_name, error=str(e))
                stats["databases"][db_name] = {"error": str(e)}
        
        return stats