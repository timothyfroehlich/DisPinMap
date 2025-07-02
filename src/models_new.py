"""
New SQLAlchemy models for Discord Pinball Map Bot Schema Redesign
Implements comprehensive database schema redesign to resolve architectural issues.

Addresses Issues #78, #81:
- Eliminates data overloading in target_name field
- Provides proper type safety with validation constraints
- Normalizes data access patterns
- Adds comprehensive data integrity constraints
"""

from typing import Optional

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
from sqlalchemy.orm import DeclarativeBase, relationship, validates
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
    """
    Redesigned monitoring targets table with proper normalization and type safety.

    Supports two distinct target types:
    - 'location': PinballMap location monitoring using location_id
    - 'geographic': Coordinate-based monitoring with latitude/longitude

    Key improvements:
    - Single responsibility for each field
    - Proper data types with validation
    - Clear semantics: display_name always human-readable
    - Comprehensive data integrity constraints
    - Prevents invalid data combinations
    """

    __tablename__ = "monitoring_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(
        BigInteger, ForeignKey("channel_configs.channel_id"), nullable=False
    )

    # Core target information
    target_type = Column(String, nullable=False)  # 'location' or 'geographic'
    display_name = Column(
        String, nullable=False
    )  # Always human-readable name for users

    # Location-specific fields (for PinballMap locations)
    location_id = Column(Integer, nullable=True)  # PinballMap location ID

    # Geographic fields (for coordinate-based monitoring)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_miles = Column(Integer, nullable=True)

    # Settings (unchanged from original schema)
    poll_rate_minutes = Column(Integer, default=60)
    notification_types = Column(String, default="machines")
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    channel_config = relationship("ChannelConfig", back_populates="monitoring_targets")

    # Data integrity constraints
    __table_args__ = (
        # Target type validation
        CheckConstraint(
            "target_type IN ('location', 'geographic')", name="valid_target_type"
        ),
        # Target data consistency - exactly one target type's fields must be populated
        CheckConstraint(
            """
            (target_type = 'location' AND location_id IS NOT NULL AND latitude IS NULL AND longitude IS NULL)
            OR
            (target_type = 'geographic' AND location_id IS NULL AND latitude IS NOT NULL AND longitude IS NOT NULL AND radius_miles IS NOT NULL)
            """,
            name="target_data_consistency",
        ),
        # Coordinate validation
        CheckConstraint(
            "latitude IS NULL OR (latitude BETWEEN -90 AND 90)", name="valid_latitude"
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude BETWEEN -180 AND 180)",
            name="valid_longitude",
        ),
        CheckConstraint(
            "radius_miles IS NULL OR (radius_miles BETWEEN 1 AND 100)",
            name="valid_radius",
        ),
        # Uniqueness constraints to prevent duplicates
        UniqueConstraint("channel_id", "location_id", name="unique_location_target"),
        UniqueConstraint(
            "channel_id",
            "latitude",
            "longitude",
            "radius_miles",
            name="unique_geographic_target",
        ),
    )

    @validates("target_type")
    def validate_target_type(self, key, target_type):
        """Validate target_type is one of the allowed values"""
        if target_type not in ("location", "geographic"):
            raise ValueError(
                f"target_type must be 'location' or 'geographic', got: {target_type}"
            )
        return target_type

    @validates("latitude")
    def validate_latitude(self, key, latitude):
        """Validate latitude is within valid range"""
        if latitude is not None and not (-90 <= latitude <= 90):
            raise ValueError(f"latitude must be between -90 and 90, got: {latitude}")
        return latitude

    @validates("longitude")
    def validate_longitude(self, key, longitude):
        """Validate longitude is within valid range"""
        if longitude is not None and not (-180 <= longitude <= 180):
            raise ValueError(
                f"longitude must be between -180 and 180, got: {longitude}"
            )
        return longitude

    @validates("radius_miles")
    def validate_radius_miles(self, key, radius_miles):
        """Validate radius_miles is within reasonable range"""
        if radius_miles is not None and not (1 <= radius_miles <= 100):
            raise ValueError(
                f"radius_miles must be between 1 and 100, got: {radius_miles}"
            )
        return radius_miles

    def is_location_target(self) -> bool:
        """Check if this is a location-based target"""
        return self.target_type == "location"

    def is_geographic_target(self) -> bool:
        """Check if this is a geographic coordinate-based target"""
        return self.target_type == "geographic"

    def get_coordinates(self) -> Optional[tuple[float, float, int]]:
        """
        Get coordinates for geographic targets.

        Returns:
            Tuple of (latitude, longitude, radius_miles) for geographic targets,
            None for location targets.
        """
        if self.is_geographic_target():
            return (self.latitude, self.longitude, self.radius_miles)
        return None

    def get_location_id(self) -> Optional[int]:
        """
        Get location ID for location targets.

        Returns:
            location_id for location targets, None for geographic targets.
        """
        if self.is_location_target():
            return self.location_id
        return None

    def format_coordinates_display(self) -> str:
        """
        Format coordinates for display in user interfaces.

        Returns:
            Formatted coordinate string for geographic targets,
            empty string for location targets.
        """
        if self.is_geographic_target():
            return (
                f"{self.latitude:.5f}, {self.longitude:.5f} ({self.radius_miles} miles)"
            )
        return ""

    def validate_data_consistency(self) -> bool:
        """
        Validate that target data is consistent with target type.

        Returns:
            True if data is consistent, False otherwise.
        """
        if self.target_type == "location":
            return (
                self.location_id is not None
                and self.latitude is None
                and self.longitude is None
            )
        elif self.target_type == "geographic":
            return (
                self.location_id is None
                and self.latitude is not None
                and self.longitude is not None
                and self.radius_miles is not None
            )
        return False

    def __repr__(self):
        if self.is_location_target():
            return f"<MonitoringTarget(type=location, id={self.location_id}, name='{self.display_name}')>"
        else:
            return f"<MonitoringTarget(type=geographic, coords=({self.latitude}, {self.longitude}), radius={self.radius_miles}, name='{self.display_name}')>"


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
