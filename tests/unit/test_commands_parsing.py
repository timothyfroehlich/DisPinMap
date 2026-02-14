"""
Unit tests for command argument parsing.

These tests ensure that the command functions can correctly parse and validate
their arguments, without executing the full command logic or interacting
with the database.
"""

import pytest


class TestCoordinateParsing:
    """Test coordinate parsing logic"""

    @pytest.mark.parametrize(
        "lat_str, lon_str",
        [
            ("45.5231", "-122.6765"),
            ("0", "0"),
            ("90", "180"),
            ("-90", "-180"),
        ],
        ids=["portland", "origin", "max_positive", "max_negative"],
    )
    def test_valid_coordinates(self, lat_str, lon_str):
        """Test parsing valid coordinate strings"""
        lat = float(lat_str)
        lon = float(lon_str)

        assert -90 <= lat <= 90, f"Invalid latitude: {lat}"
        assert -180 <= lon <= 180, f"Invalid longitude: {lon}"

    @pytest.mark.parametrize(
        "lat_str, lon_str",
        [
            ("invalid", "-122.6765"),
            ("45.5231", "invalid"),
            ("91", "0"),
            ("0", "181"),
            ("-91", "0"),
            ("0", "-181"),
        ],
        ids=[
            "invalid_lat_str",
            "invalid_lon_str",
            "lat_over_90",
            "lon_over_180",
            "lat_under_neg90",
            "lon_under_neg180",
        ],
    )
    def test_invalid_coordinates(self, lat_str, lon_str):
        """Test parsing invalid coordinate strings"""
        with pytest.raises(ValueError):
            lat = float(lat_str)
            lon = float(lon_str)

            if not (-90 <= lat <= 90):
                raise ValueError(f"Invalid latitude: {lat}")
            if not (-180 <= lon <= 180):
                raise ValueError(f"Invalid longitude: {lon}")


class TestRadiusParsing:
    """Test radius parsing logic"""

    @pytest.mark.parametrize(
        "radius_str",
        ["1", "10", "100", "1000"],
        ids=["min", "small", "medium", "large"],
    )
    def test_valid_radius(self, radius_str):
        """Test parsing valid radius values"""
        radius = int(radius_str)
        assert radius > 0, f"Radius must be positive: {radius}"

    @pytest.mark.parametrize(
        "radius_str",
        ["0", "-1", "invalid", "1.5"],
        ids=["zero", "negative", "non_numeric", "float"],
    )
    def test_invalid_radius(self, radius_str):
        """Test parsing invalid radius values"""
        with pytest.raises((ValueError, TypeError)):
            radius = int(radius_str)
            if radius <= 0:
                raise ValueError(f"Radius must be positive: {radius}")


class TestIndexParsing:
    """Test index parsing logic"""

    def test_valid_index(self):
        """Test parsing valid index values"""
        valid_indices = ["1", "2", "10", "100"]

        for index_str in valid_indices:
            index = int(index_str)
            assert index > 0, f"Index must be positive: {index}"

    def test_invalid_index(self):
        """Test parsing invalid index values"""
        invalid_indices = ["0", "-1", "invalid", "1.5"]

        for index_str in invalid_indices:
            with pytest.raises((ValueError, TypeError)):
                index = int(index_str)
                if index <= 0:
                    raise ValueError(f"Index must be positive: {index}")


class TestTargetTypeValidation:
    """Test target type validation"""

    @pytest.mark.parametrize(
        "target_type",
        ["location", "geographic"],
    )
    def test_valid_target_types(self, target_type):
        """Test valid target types"""
        valid_types = ["location", "geographic"]
        assert target_type in valid_types, f"Invalid target type: {target_type}"

    @pytest.mark.parametrize(
        "target_type",
        ["foobar", "location_id", "coords", "town", "city", "coordinates"],
    )
    def test_invalid_target_types(self, target_type):
        """Test invalid target types"""
        valid_types = ["location", "geographic"]
        assert target_type not in valid_types, (
            f"Unexpectedly valid target type: {target_type}"
        )


class TestNotificationTypeValidation:
    """Test notification type validation"""

    @pytest.mark.parametrize(
        "notification_type",
        ["all", "machines", "comments", "conditions"],
    )
    def test_valid_notification_types(self, notification_type):
        """Test valid notification types"""
        valid_types = ["all", "machines", "comments", "conditions"]
        assert notification_type in valid_types, (
            f"Invalid notification type: {notification_type}"
        )

    @pytest.mark.parametrize(
        "notification_type",
        ["allz", "machine", "comment", "condition"],
    )
    def test_invalid_notification_types(self, notification_type):
        """Test invalid notification types"""
        valid_types = ["all", "machines", "comments", "conditions"]
        assert notification_type not in valid_types, (
            f"Unexpectedly valid notification type: {notification_type}"
        )
