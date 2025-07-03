"""
SQLAlchemy models for Discord Pinball Map Bot
Defines the database schema using SQLAlchemy ORM
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
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
    is_active = Column(Boolean, default=True)
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
    """Monitoring targets table - normalized schema with proper constraints"""

    __tablename__ = "monitoring_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        BigInteger, ForeignKey("channel_configs.channel_id"), nullable=False
    )
    target_type = Column(String, nullable=False)  # 'location', 'geographic'
    display_name = Column(
        String, nullable=False
    )  # Always human-readable name for users

    # Location-specific fields (for PinballMap locations)
    location_id = Column(Integer)  # PinballMap location ID

    # Geographic fields (for coordinate-based monitoring)
    latitude = Column(Float)
    longitude = Column(Float)
    radius_miles = Column(Integer, default=25)

    # Settings (unchanged)
    poll_rate_minutes = Column(Integer, default=60)
    notification_types = Column(String, default="machines")
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    channel_config = relationship("ChannelConfig", back_populates="monitoring_targets")

    # Data integrity constraints
    __table_args__ = (
        # Ensure target type has appropriate data
        CheckConstraint(
            """
            (target_type = 'location' AND location_id IS NOT NULL AND latitude IS NULL AND longitude IS NULL)
            OR
            (target_type = 'geographic' AND location_id IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL AND radius_miles IS NOT NULL)
            """,
            name="target_data_check",
        ),
        # Validate coordinate ranges
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="valid_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="valid_longitude",
        ),
        CheckConstraint(
            "radius_miles IS NULL OR (radius_miles >= 1 AND radius_miles <= 100)",
            name="valid_radius",
        ),
        # Ensure valid target types
        CheckConstraint(
            "target_type IN ('location', 'geographic')", name="valid_target_type"
        ),
        # Uniqueness constraints
        UniqueConstraint("channel_id", "location_id", name="unique_location"),
        UniqueConstraint(
            "channel_id",
            "latitude",
            "longitude",
            name="unique_geographic",
        ),
    )

    def is_location_target(self) -> bool:
        """Check if this is a location-based target"""
        return self.target_type == "location"

    def is_geographic_target(self) -> bool:
        """Check if this is a geographic coordinate-based target"""
        return self.target_type == "geographic"

    def get_coordinates(self) -> tuple[float, float, int] | None:
        """Get coordinates for geographic targets"""
        if (
            self.is_geographic_target()
            and self.latitude is not None
            and self.longitude is not None
        ):
            return (
                float(self.latitude),
                float(self.longitude),
                int(self.radius_miles or 25),
            )
        return None

    def format_coordinates(self) -> str | None:
        """Format coordinates as a human-readable string"""
        coords = self.get_coordinates()
        if coords:
            lat, lon, radius = coords
            return f"{lat:.5f}, {lon:.5f} ({radius}mi)"
        return None

    def get_location_id(self) -> int | None:
        """Get location ID for location targets"""
        if self.is_location_target():
            return self.location_id
        return None

    def validate_data_consistency(self) -> bool:
        """Validate target data consistency based on type"""
        if self.target_type == "location":
            # Location targets must have location_id and no geographic data
            return (
                self.location_id is not None
                and self.latitude is None
                and self.longitude is None
            )
        elif self.target_type == "geographic":
            # Geographic targets must have coordinates and no location_id
            return (
                self.location_id is None
                and self.latitude is not None
                and self.longitude is not None
                and self.radius_miles is not None
                and -90 <= self.latitude <= 90
                and -180 <= self.longitude <= 180
                and 1 <= self.radius_miles <= 100
            )
        else:
            # Invalid target type
            return False

    def __repr__(self) -> str:
        """String representation for debugging"""
        if self.is_location_target():
            return f"<MonitoringTarget(id={self.id}, type='location', display_name='{self.display_name}', location_id={self.location_id})>"
        elif self.is_geographic_target():
            coords = self.format_coordinates()
            return f"<MonitoringTarget(id={self.id}, type='geographic', display_name='{self.display_name}', coords='{coords}')>"
        else:
            return f"<MonitoringTarget(id={self.id}, type='{self.target_type}', display_name='{self.display_name}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API compatibility"""
        return {
            "id": self.id,
            "channel_id": self.channel_id,
            "target_type": self.target_type,
            "display_name": self.display_name,
            "location_id": self.location_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "radius_miles": self.radius_miles,
            "poll_rate_minutes": self.poll_rate_minutes,
            "notification_types": self.notification_types,
            "last_checked_at": self.last_checked_at,
            "created_at": self.created_at,
        }


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
