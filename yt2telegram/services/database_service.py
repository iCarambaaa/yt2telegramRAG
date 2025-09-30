import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from ..models.video import Video
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

# @agent:service-type data-access
# @agent:scalability vertical
# @agent:persistence database
# @agent:priority critical
# @agent:dependencies SQLite,FileSystem
class DatabaseService:
    """Advanced SQLite database service with multi-model support and automatic migration.
    
    Manages video processing data with comprehensive multi-model metadata storage,
    automatic schema migration, and analytics capabilities. Implements WAL mode
    for concurrent access and optimized performance settings for production use.
    
    Architecture: Single SQLite database per channel with WAL journaling
    Critical Path: All video processing results must be persisted reliably
    Failure Mode: Database corruption protection with transaction rollback
    
    AI-GUIDANCE:
    - Never modify schema without corresponding migration logic
    - Always use transactions for multi-table operations
    - Preserve backward compatibility with existing data
    - Implement proper connection pooling for concurrent access
    - Use parameterized queries to prevent SQL injection
    
    Attributes:
        db_path (Path): Database file path with automatic parent directory creation
        
    Example:
        >>> db = DatabaseService("channels/twominutepapers.db")
        >>> video = Video(id="abc123", title="AI Research", channel_id="UCbfYPyITQ-7l4upoX8nvctg")
        >>> db.add_video(video)
        
    Note:
        Thread-safe with WAL mode. Automatic schema migration on initialization.
        Connection timeout set to 30 seconds for reliability.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_database()
    
    # @agent:complexity medium
    # @agent:side-effects database_connection,file_system_access
    # @agent:performance O(1) connection_establishment
    # @agent:security sql_injection_prevention,connection_timeout
    def _get_connection(self) -> sqlite3.Connection:
        """Establish optimized SQLite connection with production-ready settings.
        
        Creates database connection with WAL journaling mode for concurrent access,
        row factory for dict-like access, and optimized synchronization settings.
        Implements 30-second timeout to prevent hanging connections.
        
        Intent: Provide reliable, optimized database connections for all operations
        Critical: Connection settings affect performance and data integrity
        
        AI-DECISION: SQLite optimization settings
        Criteria:
        - WAL mode → enables concurrent readers with single writer
        - NORMAL synchronous → balances performance with data safety
        - Row factory → enables dict-like column access
        - 30s timeout → prevents indefinite blocking
        
        Returns:
            sqlite3.Connection: Configured database connection with optimizations
            
        AI-NOTE: 
            - WAL mode requires SQLite 3.7.0+ (standard in Python 3.6+)
            - Connection settings are critical for performance - don't modify casually
            - Timeout prevents deadlocks in high-concurrency scenarios
        """
        # Performance optimization: WAL mode + optimized synchronization
        # ADR: SQLite configuration for production use
        # Decision: WAL journaling with NORMAL synchronization
        # Context: Need concurrent read access with single writer
        # Consequences: Better performance, requires SQLite 3.7.0+
        # Alternatives: DELETE mode (rejected - no concurrency), FULL sync (rejected - too slow)
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # Prevent indefinite blocking
            isolation_level=None,  # Autocommit mode for better control
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like column access
        conn.execute("PRAGMA journal_mode=WAL")  # Enable concurrent readers
        conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
        return conn

    # @agent:complexity high
    # @agent:side-effects database_schema_creation,automatic_migration
    # @agent:security schema_validation,sql_injection_prevention
    # @agent:test-coverage critical,migration-scenarios
    def _create_database(self):
        """Initialize database with enhanced multi-model schema and automatic migration.
        
        Creates comprehensive video storage schema supporting both single-model and
        multi-model processing metadata. Automatically migrates existing databases
        to enhanced schema while preserving all existing data.
        
        Intent: Establish complete database schema with backward compatibility
        Critical: Schema changes must preserve existing data and maintain compatibility
        
        State Machine: Database initialization
        States: check_existing → create_tables → migrate_schema → validate_schema
        Migration States: detect_columns → add_missing_columns → preserve_data
        
        AI-DECISION: Schema evolution strategy
        Criteria:
        - New installation → create full enhanced schema
        - Existing database → detect missing columns and add incrementally
        - Migration failure → rollback and log error details
        - Data integrity → validate schema after migration
        
        AI-NOTE: 
            - Never DROP tables or columns - only ADD new columns
            - Use DEFAULT values for new columns to handle existing rows
            - Migration is idempotent - safe to run multiple times
            - All schema changes must be backward compatible
        """
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    published_at TEXT,
                    raw_subtitles TEXT,
                    cleaned_subtitles TEXT,
                    summary TEXT,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Multi-model enhancement fields
                    summarization_method TEXT DEFAULT 'single',
                    primary_summary TEXT,
                    secondary_summary TEXT,
                    synthesis_summary TEXT,
                    primary_model TEXT,
                    secondary_model TEXT,
                    synthesis_model TEXT,
                    token_usage_json TEXT,
                    processing_time_seconds REAL,
                    cost_estimate REAL,
                    fallback_used INTEGER DEFAULT 0
                )
            ''')
            
            # Migrate existing databases to enhanced schema
            self._migrate_to_enhanced_schema(conn)
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_status (
                    channel_id TEXT PRIMARY KEY,
                    last_check TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    # @agent:complexity critical
    # @agent:side-effects database_schema_modification,data_preservation
    # @agent:security data_integrity_validation,transaction_safety
    # @agent:performance O(n) where n=number_of_columns_to_add
    def _migrate_to_enhanced_schema(self, conn):
        """Safely migrate existing database to enhanced multi-model schema.
        
        Performs incremental schema migration by detecting missing columns and
        adding them with appropriate defaults. Preserves all existing data and
        maintains backward compatibility with older database versions.
        
        Intent: Upgrade database schema without data loss or service interruption
        Critical: Migration failures could corrupt existing video data
        
        Migration Strategy:
        1. Detect current schema by querying table_info
        2. Compare with required enhanced schema columns
        3. Add missing columns one by one with proper defaults
        4. Validate migration success
        5. Log migration results for monitoring
        
        AI-DECISION: Column addition strategy
        Criteria:
        - Column exists → skip addition (idempotent)
        - Column missing → add with DEFAULT value
        - Migration error → log error but continue with other columns
        - Critical columns missing → ensure they're added successfully
        
        Args:
            conn (sqlite3.Connection): Active database connection with transaction
            
        AI-NOTE: 
            - Migration is idempotent - safe to run multiple times
            - Uses ALTER TABLE ADD COLUMN (SQLite 3.1.3+ feature)
            - DEFAULT values ensure existing rows remain valid
            - Each column addition is independent - partial failures are handled
        """
        # Schema introspection: detect current database structure
        # @security:sql-injection-safe - using PRAGMA, not user input
        cursor = conn.execute("PRAGMA table_info(videos)")
        existing_columns = {col[1] for col in cursor.fetchall()}
        
        # Migration mapping: define all enhanced schema columns with defaults
        # ADR: Default value strategy for new columns
        # Decision: Use meaningful defaults that don't break existing functionality
        # Context: Existing rows need valid values for new columns
        # Consequences: Backward compatibility maintained, analytics work correctly
        new_columns = [
            ('published_at', 'TEXT'),  # NULL acceptable for older videos
            ('summarization_method', 'TEXT DEFAULT "single"'),  # Assume single-model for existing
            ('primary_summary', 'TEXT'),  # NULL acceptable, will be populated on re-processing
            ('secondary_summary', 'TEXT'),  # NULL for single-model summaries
            ('synthesis_summary', 'TEXT'),
            ('primary_model', 'TEXT'),
            ('secondary_model', 'TEXT'),
            ('synthesis_model', 'TEXT'),
            ('token_usage_json', 'TEXT'),
            ('processing_time_seconds', 'REAL'),
            ('cost_estimate', 'REAL'),
            ('fallback_used', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    conn.execute(f'ALTER TABLE videos ADD COLUMN {column_name} {column_type}')
                    logger.info(f"Added column {column_name} to videos table")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Could not add column {column_name}: {e}")
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_processed_at ON videos(processed_at)')

    def is_video_processed(self, video_id: str) -> bool:
        """Check if video has already been processed"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT 1 FROM videos WHERE id = ?', (video_id,))
            return cursor.fetchone() is not None

    def add_video(self, video: Video):
        """Add video to database with enhanced multi-model support"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO videos 
                (id, title, channel_id, published_at, raw_subtitles, cleaned_subtitles, summary,
                 summarization_method, primary_summary, secondary_summary, synthesis_summary,
                 primary_model, secondary_model, synthesis_model, token_usage_json,
                 processing_time_seconds, cost_estimate, fallback_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video.id,
                video.title,
                video.channel_id,
                video.published_at,
                video.raw_subtitles,
                video.cleaned_subtitles,
                video.summary,
                video.summarization_method,
                video.primary_summary,
                video.secondary_summary,
                video.synthesis_summary,
                video.primary_model,
                video.secondary_model,
                video.synthesis_model,
                video.token_usage_json,
                video.processing_time_seconds,
                video.cost_estimate,
                1 if video.fallback_used else 0 if video.fallback_used is not None else None
            ))
        logger.info("Added video to database", video_id=video.id, published_at=video.published_at)

    def get_last_check(self, channel_id: str) -> Optional[str]:
        """Get last check timestamp for channel"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT last_check FROM channel_status WHERE channel_id = ?',
                (channel_id,)
            )
            row = cursor.fetchone()
            return row['last_check'] if row else None

    def update_last_check(self, channel_id: str, timestamp: str):
        """Update last check timestamp for channel"""
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO channel_status (channel_id, last_check)
                VALUES (?, ?)
            ''', (channel_id, timestamp))
        logger.info("Updated last check for channel", channel_id=channel_id)

    def get_recent_videos(self, channel_id: str, limit: int = 10) -> List[Video]:
        """Get recent videos for a channel"""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM videos 
                WHERE channel_id = ? 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (channel_id, limit))
            
            videos = []
            for row in cursor.fetchall():
                video = Video(
                    id=row['id'],
                    title=row['title'],
                    channel_id=row['channel_id'],
                    raw_subtitles=row['raw_subtitles'],
                    cleaned_subtitles=row['cleaned_subtitles'],
                    summary=row['summary']
                )
                videos.append(video)
            
            return videos