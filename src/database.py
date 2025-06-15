"""
SQLAlchemy-based database module for Discord Pinball Map Bot
Replaces the old sqlite3-based database.py with modern SQLAlchemy ORM
"""

from sqlalchemy import create_engine, select, delete, update
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, List, Any
import os
import logging

logger = logging.getLogger(__name__)
try:
    from .models import Base, ChannelConfig, MonitoringTarget, SeenSubmission
except ImportError:
    from models import Base, ChannelConfig, MonitoringTarget, SeenSubmission


class Database:
    def __init__(self, db_path: str = "pinball_bot.db"):
        """Initialize database with SQLAlchemy - supports both SQLite and PostgreSQL"""
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()

        if db_type == 'postgres':
            self.engine = self._create_postgres_engine()
        else:
            # SQLite (default for local development and testing)
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

    def _create_postgres_engine(self):
        """Create PostgreSQL engine using Google Cloud SQL Connector"""
        try:
            from google.cloud.sql.connector import Connector
        except ImportError:
            logger.error("google-cloud-sql-connector not available for PostgreSQL connection")
            raise ImportError("Install google-cloud-sql-connector[pg8000] for PostgreSQL support")

        # Get required environment variables
        instance_connection_name = os.getenv('DB_INSTANCE_CONNECTION_NAME')
        db_user = os.getenv('DB_USER')
        db_name = os.getenv('DB_NAME')
        db_password_secret_name = os.getenv('DB_PASSWORD_SECRET_NAME')

        if not all([instance_connection_name, db_user, db_name, db_password_secret_name]):
            missing_vars = [var for var, val in [
                ('DB_INSTANCE_CONNECTION_NAME', instance_connection_name),
                ('DB_USER', db_user),
                ('DB_NAME', db_name),
                ('DB_PASSWORD_SECRET_NAME', db_password_secret_name)
            ] if not val]
            logger.error(f"Missing required environment variables for PostgreSQL: {missing_vars}")
            raise ValueError(f"Missing required environment variables: {missing_vars}")

        # Get database password from Secret Manager
        try:
            from google.cloud import secretmanager
            secret_client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
            if not project_id:
                logger.error("GOOGLE_CLOUD_PROJECT environment variable not set")
                raise ValueError("GOOGLE_CLOUD_PROJECT environment variable required for Secret Manager")

            secret_name = f"projects/{project_id}/secrets/{db_password_secret_name}/versions/latest"
            response = secret_client.access_secret_version(request={"name": secret_name})
            db_pass = response.payload.data.decode("UTF-8")
            logger.info("Successfully retrieved database password from Secret Manager")
        except ImportError:
            logger.error("google-cloud-secret-manager not available")
            raise ImportError("Install google-cloud-secret-manager for GCP Secret Manager support")
        except Exception as e:
            logger.error(f"Failed to retrieve database password from Secret Manager: {e}")
            raise

        # Initialize Cloud SQL Connector
        connector = Connector()

        def getconn():
            """Create database connection using Cloud SQL Connector"""
            conn = connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
            )
            return conn

        # Create SQLAlchemy engine with the connector
        engine = create_engine(
            "postgresql+pg8000://",
            creator=getconn,
            echo=False
        )

        logger.info(f"Created PostgreSQL engine for instance: {instance_connection_name}")
        return engine

    def init_database(self) -> None:
        """Initialize database tables"""
        try:
            # Drop all tables first to ensure clean state
            Base.metadata.drop_all(bind=self.engine)
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def drop_all_tables(self) -> None:
        """Drop all tables - use with caution, mainly for testing"""
        try:
            Base.metadata.drop_all(bind=self.engine)
        except Exception as e:
            logger.error(f"Error dropping database tables: {e}")
            raise

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
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    # If already exists, update instead
                    config = session.get(ChannelConfig, channel_id)
                    for key, value in kwargs.items():
                        if hasattr(config, key):
                            setattr(config, key, value)
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
    def add_monitoring_target(self, channel_id: int, target_type: str, target_name: str, target_data: str = None, poll_rate_minutes: int = None, notification_types: str = None) -> None:
        """Add a monitoring target for a channel"""
        with self.get_session() as session:
            # Get channel config for defaults
            config = session.get(ChannelConfig, channel_id)
            if not config:
                config = ChannelConfig(
                    channel_id=channel_id,
                    guild_id=0,  # Will be updated later
                    poll_rate_minutes=60,
                    notification_types='machines',
                    is_active=True
                )
                session.add(config)
                session.commit()

            # Use channel defaults if not specified
            if poll_rate_minutes is None:
                poll_rate_minutes = config.poll_rate_minutes
            if notification_types is None:
                notification_types = config.notification_types

            target = MonitoringTarget(
                channel_id=channel_id,
                target_type=target_type,
                target_name=target_name,
                target_data=target_data,
                poll_rate_minutes=poll_rate_minutes,
                notification_types=notification_types
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
            session.execute(stmt)
            session.commit()

    def update_monitoring_target(self, channel_id: int, target_type: str, target_name: str, **kwargs) -> None:
        """Update a monitoring target's settings"""
        with self.get_session() as session:
            stmt = (
                update(MonitoringTarget)
                .where(
                    MonitoringTarget.channel_id == channel_id,
                    MonitoringTarget.target_type == target_type,
                    MonitoringTarget.target_name == target_name
                )
                .values(**kwargs)
            )
            session.execute(stmt)
            session.commit()

    def get_monitoring_targets(self, channel_id: int) -> List[Dict[str, Any]]:
        """Get all monitoring targets for a channel"""
        with self.get_session() as session:
            targets = session.execute(
                select(MonitoringTarget)
                .where(MonitoringTarget.channel_id == channel_id)
                .order_by(MonitoringTarget.id)
            ).scalars().all()

            return [
                {
                    'id': target.id,
                    'channel_id': target.channel_id,
                    'target_type': target.target_type,
                    'target_name': target.target_name,
                    'target_data': target.target_data,
                    'poll_rate_minutes': target.poll_rate_minutes,
                    'notification_types': target.notification_types,
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
        with self.get_session() as session:
            for submission_id in submission_ids:
                seen = SeenSubmission(
                    channel_id=channel_id,
                    submission_id=submission_id
                )
                session.add(seen)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    # Ignore duplicate errors

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

    def get_seen_submission_ids(self, channel_id: int) -> List[int]:
        """Get list of seen submission IDs for a channel"""
        with self.get_session() as session:
            seen = session.execute(
                select(SeenSubmission.submission_id)
                .where(SeenSubmission.channel_id == channel_id)
            ).scalars().all()
            return list(seen)

    def clear_seen_submissions(self, channel_id: int) -> None:
        """Clear seen submissions for a channel"""
        with self.get_session() as session:
            stmt = delete(SeenSubmission).where(SeenSubmission.channel_id == channel_id)
            session.execute(stmt)
            session.commit()
