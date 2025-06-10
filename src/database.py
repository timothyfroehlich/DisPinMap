"""
SQLAlchemy-based database module for Discord Pinball Map Bot
Replaces the old sqlite3-based database.py with modern SQLAlchemy ORM
"""

from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, List, Any
try:
    from .models import Base, ChannelConfig, MonitoringTarget, SeenSubmission
except ImportError:
    from models import Base, ChannelConfig, MonitoringTarget, SeenSubmission


class Database:
    def __init__(self, db_path: str = "pinball_bot.db"):
        """Initialize database with SQLAlchemy"""
        if db_path == ":memory:":
            # For in-memory databases (testing)
            self.engine = create_engine("sqlite:///:memory:", echo=False)
        else:
            # For file databases
            self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create all tables
        self.init_database()
    
    def init_database(self) -> None:
        """Initialize database tables"""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def close(self) -> None:
        """Close database connections"""
        self.engine.dispose()
    
    # Channel configuration methods
    def get_channel_config(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific channel"""
        try:
            with self.get_session() as session:
                config = session.get(ChannelConfig, channel_id)
                if config:
                    return {
                        'channel_id': config.channel_id,
                        'guild_id': config.guild_id,
                        'poll_rate_minutes': config.poll_rate_minutes,
                        'notification_types': config.notification_types,
                        'is_active': config.is_active,
                        'created_at': config.created_at,
                        'updated_at': config.updated_at
                    }
                return None
        except Exception:
            return None
    
    def update_channel_config(self, channel_id: int, guild_id: int, **kwargs) -> None:
        """Update or create channel configuration"""
        with self.get_session() as session:
            config = session.get(ChannelConfig, channel_id)
            
            if config:
                # Update existing config
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            else:
                # Create new config
                config = ChannelConfig(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    poll_rate_minutes=kwargs.get('poll_rate_minutes', 60),
                    notification_types=kwargs.get('notification_types', 'machines'),
                    is_active=kwargs.get('is_active', False)
                )
                session.add(config)
            
            session.commit()
    
    def get_active_channels(self) -> List[Dict[str, Any]]:
        """Get all channels that are actively monitoring"""
        with self.get_session() as session:
            # First get all active channel configs
            active_configs = session.execute(
                select(ChannelConfig).where(ChannelConfig.is_active == True)
            ).scalars().all()
            
            # Filter to only those that have monitoring targets
            configs = []
            for config in active_configs:
                targets_count = session.execute(
                    select(MonitoringTarget).where(MonitoringTarget.channel_id == config.channel_id)
                ).scalars().first()
                if targets_count:
                    configs.append(config)
            
            return [
                {
                    'channel_id': config.channel_id,
                    'guild_id': config.guild_id,
                    'poll_rate_minutes': config.poll_rate_minutes,
                    'notification_types': config.notification_types,
                    'is_active': config.is_active,
                    'created_at': config.created_at,
                    'updated_at': config.updated_at
                }
                for config in configs
            ]
    
    # Monitoring target methods
    def add_monitoring_target(self, channel_id: int, target_type: str, target_name: str, target_data: str = None, poll_rate_minutes: int = 60) -> None:
        """Add a monitoring target for a channel"""
        with self.get_session() as session:
            target = MonitoringTarget(
                channel_id=channel_id,
                target_type=target_type,
                target_name=target_name,
                target_data=target_data,
                poll_rate_minutes=poll_rate_minutes
            )
            session.add(target)
            
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise Exception(f"Target '{target_name}' of type '{target_type}' is already being monitored")
    
    def remove_monitoring_target(self, channel_id: int, target_type: str, target_name: str) -> None:
        """Remove a monitoring target for a channel"""
        with self.get_session() as session:
            stmt = delete(MonitoringTarget).where(
                MonitoringTarget.channel_id == channel_id,
                MonitoringTarget.target_type == target_type,
                MonitoringTarget.target_name == target_name
            )
            result = session.execute(stmt)
            
            if result.rowcount == 0:
                raise Exception(f"Target '{target_name}' of type '{target_type}' not found")
            
            session.commit()
    
    def get_monitoring_targets(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get all monitoring targets for a channel, ordered by ID for consistent numbering"""
        with self.get_session() as session:
            stmt = (
                select(MonitoringTarget)
                .where(MonitoringTarget.channel_id == channel_id)
                .order_by(MonitoringTarget.id)
            )
            targets = session.execute(stmt).scalars().all()
            
            return [
                {
                    'id': target.id,
                    'channel_id': target.channel_id,
                    'target_type': target.target_type,
                    'target_name': target.target_name,
                    'target_data': target.target_data,
                    'poll_rate_minutes': target.poll_rate_minutes,
                    'created_at': target.created_at
                }
                for target in targets
            ]
    
    def clear_monitoring_targets(self, channel_id: int) -> None:
        """Remove all monitoring targets for a channel"""
        with self.get_session() as session:
            stmt = delete(MonitoringTarget).where(MonitoringTarget.channel_id == channel_id)
            session.execute(stmt)
            session.commit()
    
    def update_monitoring_target_poll_rate(self, target_id: int, poll_rate_minutes: int) -> bool:
        """Update poll rate for a specific monitoring target"""
        with self.get_session() as session:
            target = session.get(MonitoringTarget, target_id)
            if target:
                target.poll_rate_minutes = poll_rate_minutes
                session.commit()
                return True
            return False
    
    def update_channel_monitoring_targets_poll_rate(self, channel_id: int, poll_rate_minutes: int) -> int:
        """Update poll rate for all monitoring targets in a channel. Returns number of targets updated."""
        with self.get_session() as session:
            stmt = select(MonitoringTarget).where(MonitoringTarget.channel_id == channel_id)
            targets = session.execute(stmt).scalars().all()
            
            for target in targets:
                target.poll_rate_minutes = poll_rate_minutes
            
            session.commit()
            return len(targets)
    
    # Seen submissions methods
    def mark_submissions_seen(self, channel_id: int, submission_ids: List[int]) -> None:
        """Mark submissions as seen for a channel"""
        if not submission_ids:
            return
        
        with self.get_session() as session:
            for submission_id in submission_ids:
                # Check if already exists to avoid integrity errors
                existing = session.execute(
                    select(SeenSubmission).where(
                        SeenSubmission.channel_id == channel_id,
                        SeenSubmission.submission_id == submission_id
                    )
                ).scalars().first()
                
                if not existing:
                    seen_submission = SeenSubmission(
                        channel_id=channel_id,
                        submission_id=submission_id
                    )
                    session.add(seen_submission)
            
            session.commit()
    
    def filter_new_submissions(self, channel_id: int, submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out submissions we've already seen"""
        if not submissions:
            return []
        
        with self.get_session() as session:
            submission_ids = [s['id'] for s in submissions]
            
            stmt = (
                select(SeenSubmission.submission_id)
                .where(
                    SeenSubmission.channel_id == channel_id,
                    SeenSubmission.submission_id.in_(submission_ids)
                )
            )
            seen_ids = set(session.execute(stmt).scalars().all())
            
            # Return only unseen submissions
            return [s for s in submissions if s['id'] not in seen_ids]
    
    def get_seen_submissions(self, channel_id: int) -> List[int]:
        """Get list of seen submission IDs for a channel"""
        with self.get_session() as session:
            stmt = (
                select(SeenSubmission.submission_id)
                .where(SeenSubmission.channel_id == channel_id)
            )
            return list(session.execute(stmt).scalars().all())
    
    def clear_seen_submissions(self, channel_id: int) -> None:
        """Clear seen submissions for a channel"""
        with self.get_session() as session:
            stmt = delete(SeenSubmission).where(SeenSubmission.channel_id == channel_id)
            session.execute(stmt)
            session.commit()