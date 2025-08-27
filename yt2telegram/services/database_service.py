import sqlite3
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from ..models.video import Video
from ..models.multi_model import TokenUsage, MultiModelResult
from ..utils.logging_config import LoggerFactory

logger = LoggerFactory.create_logger(__name__)

class DatabaseService:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_database()
        self._migrate_if_needed()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with optimized settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            isolation_level=None,  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _create_database(self):
        """Initialize database tables - only create basic schema for legacy compatibility"""
        with self._get_connection() as conn:
            # Check if this is a fresh database or existing one
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                # Fresh install - create full schema
                conn.execute('''
                    CREATE TABLE videos (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        raw_subtitles TEXT,
                        cleaned_subtitles TEXT,
                        summary TEXT,
                        primary_summary TEXT,
                        secondary_summary TEXT,
                        synthesis_summary TEXT,
                        summarization_method TEXT DEFAULT 'single',
                        primary_model TEXT,
                        secondary_model TEXT,
                        synthesis_model TEXT,
                        token_usage_json TEXT,
                        processing_time_seconds REAL,
                        fallback_used INTEGER DEFAULT 0,
                        fallback_strategy TEXT,
                        error_details TEXT,
                        processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            else:
                # Existing database - ensure basic structure exists
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        raw_subtitles TEXT,
                        cleaned_subtitles TEXT,
                        summary TEXT,
                        processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS channel_status (
                    channel_id TEXT PRIMARY KEY,
                    last_check TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance (only if table has processed_at column)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos(channel_id)')
            try:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_videos_processed_at ON videos(processed_at)')
            except sqlite3.OperationalError:
                # Column doesn't exist yet, will be added during migration
                pass

    def _migrate_if_needed(self):
        """Check and perform database migration if needed"""
        try:
            if not self._is_migrated():
                logger.info("Database migration needed, starting migration process")
                self._perform_migration()
                self._validate_migration()
                logger.info("Database migration completed successfully")
            else:
                logger.debug("Database is already migrated")
        except Exception as e:
            logger.error("Database migration failed", error=str(e))
            raise

    def _is_migrated(self) -> bool:
        """Check if database has been migrated to multi-model schema"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("PRAGMA table_info(videos)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Check for key multi-model columns
                required_columns = [
                    'summarization_method',
                    'primary_summary',
                    'secondary_summary',
                    'synthesis_summary',
                    'token_usage_json',
                    'processing_time_seconds',
                    'fallback_used'
                ]
                
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    logger.debug("Migration needed, missing columns", missing_columns=missing_columns)
                    return False
                
                return True
                
        except Exception as e:
            logger.error("Error checking migration status", error=str(e))
            return False

    def _create_backup(self) -> str:
        """Create backup of database before migration"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.db_path}.backup_{timestamp}"
        
        try:
            if self.db_path.exists():
                shutil.copy2(self.db_path, backup_path)
                logger.info("Database backup created", backup_path=backup_path)
            return backup_path
        except Exception as e:
            logger.error("Failed to create database backup", error=str(e))
            raise

    def _perform_migration(self):
        """Migrate database to multi-model schema with comprehensive error handling"""
        backup_path = None
        
        try:
            # Create backup before migration
            backup_path = self._create_backup()
            
            with self._get_connection() as conn:
                # Start transaction
                conn.execute("BEGIN TRANSACTION")
                
                # Migration queries - add new columns
                migration_queries = [
                    "ALTER TABLE videos ADD COLUMN primary_summary TEXT",
                    "ALTER TABLE videos ADD COLUMN secondary_summary TEXT", 
                    "ALTER TABLE videos ADD COLUMN synthesis_summary TEXT",
                    "ALTER TABLE videos ADD COLUMN summarization_method TEXT DEFAULT 'single'",
                    "ALTER TABLE videos ADD COLUMN primary_model TEXT",
                    "ALTER TABLE videos ADD COLUMN secondary_model TEXT",
                    "ALTER TABLE videos ADD COLUMN synthesis_model TEXT",
                    "ALTER TABLE videos ADD COLUMN token_usage_json TEXT",
                    "ALTER TABLE videos ADD COLUMN processing_time_seconds REAL",
                    "ALTER TABLE videos ADD COLUMN fallback_used INTEGER DEFAULT 0",
                    "ALTER TABLE videos ADD COLUMN fallback_strategy TEXT",
                    "ALTER TABLE videos ADD COLUMN error_details TEXT"
                ]
                
                # Execute migration queries
                for query in migration_queries:
                    try:
                        conn.execute(query)
                        logger.debug("Executed migration query", query=query)
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e).lower():
                            logger.error("Migration query failed", query=query, error=str(e))
                            raise
                        else:
                            logger.debug("Column already exists, skipping", query=query)
                
                # Migrate existing data
                logger.info("Migrating existing video data")
                conn.execute("""
                    UPDATE videos 
                    SET primary_summary = COALESCE(primary_summary, summary),
                        summarization_method = COALESCE(summarization_method, 'single'),
                        fallback_used = COALESCE(fallback_used, 0)
                    WHERE primary_summary IS NULL OR summarization_method IS NULL
                """)
                
                # Commit transaction
                conn.execute("COMMIT")
                logger.info("Database migration transaction committed")
                
        except Exception as e:
            logger.error("Database migration failed", error=str(e))
            
            # Attempt rollback
            try:
                with self._get_connection() as conn:
                    conn.execute("ROLLBACK")
                logger.info("Migration transaction rolled back")
            except Exception as rollback_error:
                logger.error("Failed to rollback migration", error=str(rollback_error))
            
            # Restore from backup if available
            if backup_path and Path(backup_path).exists():
                try:
                    shutil.copy2(backup_path, self.db_path)
                    logger.info("Database restored from backup", backup_path=backup_path)
                except Exception as restore_error:
                    logger.error("Failed to restore from backup", error=str(restore_error))
            
            raise

    def _validate_migration(self):
        """Validate migration was successful and data integrity is maintained"""
        try:
            with self._get_connection() as conn:
                # Check all expected columns exist
                cursor = conn.execute("PRAGMA table_info(videos)")
                columns = [row[1] for row in cursor.fetchall()]
                
                expected_columns = [
                    'id', 'title', 'channel_id', 'raw_subtitles', 'cleaned_subtitles', 'summary',
                    'primary_summary', 'secondary_summary', 'synthesis_summary',
                    'summarization_method', 'primary_model', 'secondary_model', 'synthesis_model',
                    'token_usage_json', 'processing_time_seconds', 'fallback_used',
                    'fallback_strategy', 'error_details', 'processed_at'
                ]
                
                missing_columns = [col for col in expected_columns if col not in columns]
                if missing_columns:
                    raise ValueError(f"Migration incomplete: missing columns {missing_columns}")
                
                # Verify data integrity - check that existing records have been migrated
                cursor = conn.execute("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN summary IS NOT NULL AND primary_summary IS NULL THEN 1 ELSE 0 END) as unmigrated
                    FROM videos
                """)
                result = cursor.fetchone()
                
                unmigrated_count = result['unmigrated'] or 0
                if unmigrated_count > 0:
                    logger.warning(f"Found {unmigrated_count} records that may need data migration")
                
                # Verify summarization_method is set for all records
                cursor = conn.execute("SELECT COUNT(*) FROM videos WHERE summarization_method IS NULL")
                null_method_count = cursor.fetchone()[0]
                
                if null_method_count > 0:
                    raise ValueError(f"Migration incomplete: {null_method_count} records have NULL summarization_method")
                
                # Log migration statistics
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(CASE WHEN summarization_method = 'single' THEN 1 ELSE 0 END) as single_model,
                        SUM(CASE WHEN summarization_method = 'multi-model' THEN 1 ELSE 0 END) as multi_model
                    FROM videos
                """)
                stats = cursor.fetchone()
                
                logger.info("Migration validation completed", 
                          total_videos=stats['total_videos'],
                          single_model=stats['single_model'], 
                          multi_model=stats['multi_model'])
                
        except Exception as e:
            logger.error("Migration validation failed", error=str(e))
            raise

    def is_video_processed(self, video_id: str) -> bool:
        """Check if video has already been processed"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT 1 FROM videos WHERE id = ?', (video_id,))
            return cursor.fetchone() is not None

    def add_video(self, video: Video):
        """Add video to database (backward compatibility method)"""
        # Use the new multi-model method for consistency
        self.add_video_with_multi_model_data(video, None)

    def add_video_with_multi_model_data(self, video: Video, multi_model_result: Optional[MultiModelResult] = None):
        """Add video with optional multi-model data"""
        if multi_model_result:
            self._populate_multi_model_data(video, multi_model_result)
        else:
            self._populate_single_model_data(video)
        
        self._insert_video(video)

    def _populate_multi_model_data(self, video: Video, result: MultiModelResult):
        """Populate video with multi-model result data"""
        video.primary_summary = result.primary_summary
        video.secondary_summary = result.secondary_summary
        video.synthesis_summary = result.final_summary
        video.summary = result.final_summary  # Backward compatibility
        video.summarization_method = 'multi-model'
        video.token_usage = result.token_usage
        video.processing_time_seconds = result.processing_time
        video.fallback_used = result.fallback_used
        video.fallback_strategy = result.fallback_strategy.value if result.fallback_strategy else None
        video.error_details = result.error_details

    def _populate_single_model_data(self, video: Video):
        """Populate video with single-model data"""
        video.primary_summary = video.summary
        video.summarization_method = 'single'
        video.fallback_used = False

    def _insert_video(self, video: Video):
        """Insert video with all fields into database"""
        token_usage_json = None
        if video.token_usage:
            token_usage_json = json.dumps({
                'primary_model_tokens': video.token_usage.primary_model_tokens,
                'secondary_model_tokens': video.token_usage.secondary_model_tokens,
                'synthesis_model_tokens': video.token_usage.synthesis_model_tokens,
                'total_tokens': video.token_usage.total_tokens,
                'estimated_cost': video.token_usage.estimated_cost
            })

        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO videos 
                (id, title, channel_id, raw_subtitles, cleaned_subtitles, summary,
                 primary_summary, secondary_summary, synthesis_summary, summarization_method,
                 primary_model, secondary_model, synthesis_model, token_usage_json,
                 processing_time_seconds, fallback_used, fallback_strategy, error_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video.id, video.title, video.channel_id, video.raw_subtitles,
                video.cleaned_subtitles, video.summary, video.primary_summary,
                video.secondary_summary, video.synthesis_summary, video.summarization_method,
                video.primary_model, video.secondary_model, video.synthesis_model,
                token_usage_json, video.processing_time_seconds,
                int(video.fallback_used), video.fallback_strategy, video.error_details
            ))
        logger.info("Added video with multi-model data to database", video_id=video.id)

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
                # Deserialize token usage if present
                token_usage = None
                if row['token_usage_json']:
                    try:
                        token_data = json.loads(row['token_usage_json'])
                        token_usage = TokenUsage(**token_data)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning("Failed to deserialize token usage", video_id=row['id'], error=str(e))
                
                video = Video(
                    id=row['id'],
                    title=row['title'],
                    channel_id=row['channel_id'],
                    raw_subtitles=row['raw_subtitles'],
                    cleaned_subtitles=row['cleaned_subtitles'],
                    summary=row['summary'],
                    primary_summary=row['primary_summary'],
                    secondary_summary=row['secondary_summary'],
                    synthesis_summary=row['synthesis_summary'],
                    summarization_method=row['summarization_method'] or 'single',
                    primary_model=row['primary_model'],
                    secondary_model=row['secondary_model'],
                    synthesis_model=row['synthesis_model'],
                    processing_time_seconds=row['processing_time_seconds'],
                    fallback_used=bool(row['fallback_used'] or 0),
                    fallback_strategy=row['fallback_strategy'],
                    error_details=row['error_details'],
                    token_usage=token_usage
                )
                videos.append(video)
            
            return videos

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get a single video by ID"""
        with self._get_connection() as conn:
            cursor = conn.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Deserialize token usage if present
            token_usage = None
            if row['token_usage_json']:
                try:
                    token_data = json.loads(row['token_usage_json'])
                    token_usage = TokenUsage(**token_data)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Failed to deserialize token usage", video_id=row['id'], error=str(e))
            
            return Video(
                id=row['id'],
                title=row['title'],
                channel_id=row['channel_id'],
                raw_subtitles=row['raw_subtitles'],
                cleaned_subtitles=row['cleaned_subtitles'],
                summary=row['summary'],
                primary_summary=row['primary_summary'],
                secondary_summary=row['secondary_summary'],
                synthesis_summary=row['synthesis_summary'],
                summarization_method=row['summarization_method'] or 'single',
                primary_model=row['primary_model'],
                secondary_model=row['secondary_model'],
                synthesis_model=row['synthesis_model'],
                processing_time_seconds=row['processing_time_seconds'],
                fallback_used=bool(row['fallback_used'] or 0),
                fallback_strategy=row['fallback_strategy'],
                error_details=row['error_details'],
                token_usage=token_usage
            )

    def get_analytics_summary(self, channel_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Get comprehensive analytics summary for performance metrics"""
        with self._get_connection() as conn:
            where_conditions = []
            params = []
            
            if channel_id:
                where_conditions.append("channel_id = ?")
                params.append(channel_id)
            
            if start_date:
                where_conditions.append("processed_at >= ?")
                params.append(start_date)
                
            if end_date:
                where_conditions.append("processed_at <= ?")
                params.append(end_date)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Basic statistics
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_videos,
                    SUM(CASE WHEN summarization_method = 'multi-model' THEN 1 ELSE 0 END) as multi_model_count,
                    SUM(CASE WHEN summarization_method = 'single' THEN 1 ELSE 0 END) as single_model_count,
                    SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallback_count,
                    AVG(processing_time_seconds) as avg_processing_time,
                    MIN(processing_time_seconds) as min_processing_time,
                    MAX(processing_time_seconds) as max_processing_time,
                    SUM(CASE WHEN token_usage_json IS NOT NULL THEN 
                        json_extract(token_usage_json, '$.total_tokens') ELSE 0 END) as total_tokens,
                    SUM(CASE WHEN token_usage_json IS NOT NULL THEN 
                        json_extract(token_usage_json, '$.estimated_cost') ELSE 0 END) as total_estimated_cost,
                    AVG(CASE WHEN token_usage_json IS NOT NULL THEN 
                        json_extract(token_usage_json, '$.total_tokens') ELSE NULL END) as avg_tokens_per_video,
                    AVG(CASE WHEN token_usage_json IS NOT NULL THEN 
                        json_extract(token_usage_json, '$.estimated_cost') ELSE NULL END) as avg_cost_per_video
                FROM videos {where_clause}
            """, params)
            
            result = dict(cursor.fetchone())
            
            # Add percentage calculations
            if result['total_videos'] > 0:
                result['multi_model_percentage'] = (result['multi_model_count'] / result['total_videos']) * 100
                result['fallback_percentage'] = (result['fallback_count'] / result['total_videos']) * 100
                result['success_rate'] = ((result['total_videos'] - result['fallback_count']) / result['total_videos']) * 100
            else:
                result['multi_model_percentage'] = 0
                result['fallback_percentage'] = 0
                result['success_rate'] = 0
            
            # Get method effectiveness analysis
            result['method_effectiveness'] = self._get_method_effectiveness_analysis(where_clause, params)
            
            # Get fallback analysis
            result['fallback_analysis'] = self._get_fallback_analysis(where_clause, params)
            
            # Get processing time analysis
            result['processing_analysis'] = self._get_processing_time_analysis(where_clause, params)
            
            return result

    def get_token_usage_by_channel_and_date(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Get token usage aggregation by channel and date"""
        with self._get_connection() as conn:
            where_conditions = ["token_usage_json IS NOT NULL"]
            params = []
            
            if start_date:
                where_conditions.append("processed_at >= ?")
                params.append(start_date)
                
            if end_date:
                where_conditions.append("processed_at <= ?")
                params.append(end_date)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            cursor = conn.execute(f"""
                SELECT 
                    channel_id,
                    DATE(processed_at) as date,
                    COUNT(*) as video_count,
                    SUM(json_extract(token_usage_json, '$.total_tokens')) as total_tokens,
                    SUM(json_extract(token_usage_json, '$.estimated_cost')) as total_cost,
                    AVG(json_extract(token_usage_json, '$.total_tokens')) as avg_tokens,
                    AVG(json_extract(token_usage_json, '$.estimated_cost')) as avg_cost,
                    SUM(json_extract(token_usage_json, '$.primary_model_tokens')) as primary_tokens,
                    SUM(json_extract(token_usage_json, '$.secondary_model_tokens')) as secondary_tokens,
                    SUM(json_extract(token_usage_json, '$.synthesis_model_tokens')) as synthesis_tokens
                FROM videos {where_clause}
                GROUP BY channel_id, DATE(processed_at)
                ORDER BY date DESC, channel_id
            """, params)
            
            return [dict(row) for row in cursor.fetchall()]

    def get_cost_tracking_report(self, channel_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Get comprehensive cost tracking and reporting"""
        with self._get_connection() as conn:
            where_conditions = ["token_usage_json IS NOT NULL"]
            params = []
            
            if channel_id:
                where_conditions.append("channel_id = ?")
                params.append(channel_id)
            
            if start_date:
                where_conditions.append("processed_at >= ?")
                params.append(start_date)
                
            if end_date:
                where_conditions.append("processed_at <= ?")
                params.append(end_date)
            
            where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Overall cost summary
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_videos,
                    SUM(json_extract(token_usage_json, '$.total_tokens')) as total_tokens,
                    SUM(json_extract(token_usage_json, '$.estimated_cost')) as total_cost,
                    AVG(json_extract(token_usage_json, '$.estimated_cost')) as avg_cost_per_video,
                    MIN(json_extract(token_usage_json, '$.estimated_cost')) as min_cost,
                    MAX(json_extract(token_usage_json, '$.estimated_cost')) as max_cost
                FROM videos {where_clause}
            """, params)
            
            cost_summary = dict(cursor.fetchone())
            
            # Cost by summarization method
            cursor = conn.execute(f"""
                SELECT 
                    summarization_method,
                    COUNT(*) as video_count,
                    SUM(json_extract(token_usage_json, '$.estimated_cost')) as total_cost,
                    AVG(json_extract(token_usage_json, '$.estimated_cost')) as avg_cost
                FROM videos {where_clause}
                GROUP BY summarization_method
            """, params)
            
            cost_by_method = [dict(row) for row in cursor.fetchall()]
            
            # Daily cost trends
            cursor = conn.execute(f"""
                SELECT 
                    DATE(processed_at) as date,
                    COUNT(*) as video_count,
                    SUM(json_extract(token_usage_json, '$.estimated_cost')) as daily_cost,
                    AVG(json_extract(token_usage_json, '$.estimated_cost')) as avg_cost_per_video
                FROM videos {where_clause}
                GROUP BY DATE(processed_at)
                ORDER BY date DESC
                LIMIT 30
            """, params)
            
            daily_trends = [dict(row) for row in cursor.fetchall()]
            
            return {
                'summary': cost_summary,
                'by_method': cost_by_method,
                'daily_trends': daily_trends
            }

    def _get_method_effectiveness_analysis(self, where_clause: str, params: tuple) -> Dict:
        """Analyze effectiveness of different summarization methods"""
        with self._get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT 
                    summarization_method,
                    COUNT(*) as count,
                    AVG(processing_time_seconds) as avg_processing_time,
                    SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallback_count,
                    AVG(CASE WHEN token_usage_json IS NOT NULL THEN 
                        json_extract(token_usage_json, '$.estimated_cost') ELSE NULL END) as avg_cost
                FROM videos {where_clause}
                GROUP BY summarization_method
            """, params)
            
            methods = {}
            for row in cursor.fetchall():
                method_data = dict(row)
                if method_data['count'] > 0:
                    method_data['fallback_rate'] = (method_data['fallback_count'] / method_data['count']) * 100
                    method_data['success_rate'] = 100 - method_data['fallback_rate']
                else:
                    method_data['fallback_rate'] = 0
                    method_data['success_rate'] = 0
                methods[method_data['summarization_method']] = method_data
            
            return methods

    def _get_fallback_analysis(self, where_clause: str, params: tuple) -> Dict:
        """Analyze fallback frequency and reasons"""
        with self._get_connection() as conn:
            # Fallback frequency by strategy
            fallback_where = "WHERE fallback_used = 1"
            if where_clause:
                fallback_where = f"{where_clause} AND fallback_used = 1"
            
            cursor = conn.execute(f"""
                SELECT 
                    fallback_strategy,
                    COUNT(*) as count,
                    AVG(processing_time_seconds) as avg_processing_time
                FROM videos {fallback_where}
                GROUP BY fallback_strategy
            """, params)
            
            fallback_strategies = [dict(row) for row in cursor.fetchall()]
            
            # Recent fallbacks with error details
            cursor = conn.execute(f"""
                SELECT 
                    id, title, fallback_strategy, error_details, processed_at
                FROM videos {fallback_where}
                ORDER BY processed_at DESC
                LIMIT 10
            """, params)
            
            recent_fallbacks = [dict(row) for row in cursor.fetchall()]
            
            return {
                'strategies': fallback_strategies,
                'recent_fallbacks': recent_fallbacks
            }

    def _get_processing_time_analysis(self, where_clause: str, params: tuple) -> Dict:
        """Analyze processing times and identify bottlenecks"""
        with self._get_connection() as conn:
            # Processing time percentiles
            time_where = "WHERE processing_time_seconds IS NOT NULL"
            if where_clause:
                time_where = f"{where_clause} AND processing_time_seconds IS NOT NULL"
            
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_count,
                    AVG(processing_time_seconds) as avg_time,
                    MIN(processing_time_seconds) as min_time,
                    MAX(processing_time_seconds) as max_time
                FROM videos {time_where}
            """, params)
            
            time_stats = dict(cursor.fetchone())
            
            # Time distribution by method
            cursor = conn.execute(f"""
                SELECT 
                    summarization_method,
                    COUNT(*) as count,
                    AVG(processing_time_seconds) as avg_time,
                    MIN(processing_time_seconds) as min_time,
                    MAX(processing_time_seconds) as max_time
                FROM videos {time_where}
                GROUP BY summarization_method
            """, params)
            
            time_by_method = [dict(row) for row in cursor.fetchall()]
            
            # Identify slow processing videos (top 10% by time)
            cursor = conn.execute(f"""
                SELECT 
                    id, title, processing_time_seconds, summarization_method, fallback_used
                FROM videos {time_where}
                ORDER BY processing_time_seconds DESC
                LIMIT 10
            """, params)
            
            slow_videos = [dict(row) for row in cursor.fetchall()]
            
            return {
                'overall_stats': time_stats,
                'by_method': time_by_method,
                'slowest_videos': slow_videos
            }