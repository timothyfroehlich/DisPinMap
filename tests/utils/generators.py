"""
Test data generators.

This module provides functions to generate test data for various entities
used in testing, such as locations, submissions, and coordinates.
"""

import random
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta, timezone

def generate_coordinates() -> Tuple[float, float]:
    """Generate random coordinates within reasonable bounds."""
    lat = random.uniform(-90, 90)
    lon = random.uniform(-180, 180)
    return round(lat, 6), round(lon, 6)

def generate_location_data(
    location_id: Optional[int] = None,
    name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    machine_count: Optional[int] = None
) -> Dict[str, Any]:
    """Generate test data for a location."""
    if location_id is None:
        location_id = random.randint(1, 1000)
    if name is None:
        name = f"Test Location {location_id}"
    if lat is None or lon is None:
        lat, lon = generate_coordinates()
    if machine_count is None:
        machine_count = random.randint(0, 10)

    return {
        "id": location_id,
        "name": name,
        "lat": lat,
        "lon": lon,
        "machine_count": machine_count,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

def generate_submission_data(
    location_id: int,
    machine_id: Optional[int] = None,
    machine_name: Optional[str] = None,
    submission_type: str = "new_machine",
    created_at: Optional[datetime] = None,
    comment: Optional[str] = None
) -> Dict[str, Any]:
    """Generate test data for a submission."""
    if machine_id is None:
        machine_id = random.randint(1, 1000)
    if machine_name is None:
        machine_name = f"Test Machine {machine_id}"
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    data = {
        "id": random.randint(1, 1000),
        "location_id": location_id,
        "machine_id": machine_id,
        "machine_name": machine_name,
        "submission_type": submission_type,
        "created_at": created_at.isoformat()
    }
    if comment is not None:
        data["comment"] = comment
    return data

def generate_city_data(
    name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Dict[str, Any]:
    """Generate test data for a city."""
    if name is None:
        name = f"Test City {random.randint(1, 1000)}"
    if lat is None or lon is None:
        lat, lon = generate_coordinates()

    return {
        "name": name,
        "lat": lat,
        "lon": lon
    }

def generate_error_data(
    error_type: str = "validation_error",
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Generate test data for an error response."""
    if message is None:
        message = f"Test error message for {error_type}"

    return {
        "error": {
            "type": error_type,
            "message": message
        }
    }

def generate_submission_sequence(
    location_id: int,
    count: int,
    start_time: Optional[datetime] = None,
    interval_minutes: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate a sequence of submissions with timestamps.

    Args:
        location_id: ID of the location
        count: Number of submissions to generate
        start_time: Start time for the sequence (defaults to now)
        interval_minutes: Minutes between submissions

    Returns:
        List of submission data dictionaries
    """
    if start_time is None:
        start_time = datetime.utcnow()

    submissions = []
    for i in range(count):
        created_at = start_time + timedelta(minutes=i * interval_minutes)
        submissions.append(generate_submission_data(
            location_id=location_id,
            created_at=created_at
        ))

    return submissions
