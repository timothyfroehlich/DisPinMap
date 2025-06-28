"""
SQLAlchemy models for Discord Pinball Map Bot
Defines the database schema using SQLAlchemy ORM
"""

# from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class ChannelConfig(Base):
    """Channel configuration table - general settings only"""

    __tablename__ = "channel_configs"

    channel_id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    poll_rate_minutes = Column(Integer, default=60)
    notification_types = Column(String, default="machines")
    is_active = Column(Boolean, default=False)
    last_poll_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    monitoring_targets = relationship(
        "MonitoringTarget",
        back_populates="channel_config",
        cascade="all, delete-orphan",
    )
    seen_submissions = relationship(
        "SeenSubmission", back_populates="channel_config", cascade="all, delete-orphan"
    )


class MonitoringTarget(Base):
    """Monitoring targets table - supports coordinate and location targets"""

    __tablename__ = "monitoring_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        BigInteger, ForeignKey("channel_configs.channel_id"), nullable=False
    )
    target_type = Column(String, nullable=False)  # 'latlong', 'location'
    target_name = Column(String, nullable=False)  # "lat,lon,radius" or location name
    location_id = Column(Integer)  # location_id for location targets
    poll_rate_minutes = Column(Integer, default=60)  # Individual poll rate per target
    notification_types = Column(
        String, default="machines"
    )  # Per-target notification type
    last_checked_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Last time this target was checked
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    channel_config = relationship("ChannelConfig", back_populates="monitoring_targets")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "channel_id", "target_type", "location_id", name="unique_channel_location"
        ),
    )


class SeenSubmission(Base):
    """Seen submissions table - tracks which submissions we've already posted"""

    __tablename__ = "seen_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        BigInteger, ForeignKey("channel_configs.channel_id"), nullable=False
    )
    submission_id = Column(BigInteger, nullable=False)
    seen_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    channel_config = relationship("ChannelConfig", back_populates="seen_submissions")

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "channel_id", "submission_id", name="unique_channel_submission"
        ),
    )
