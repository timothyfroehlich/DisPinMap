#!/usr/bin/env python3
"""
Setup Test Cities for Local Development

Initializes the console interface with 10 major pinball cities for active testing.
All locations will be added to the fake console channel (ID: 888888888).
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import Database
from src.models import ChannelConfig, MonitoringTarget


# Major pinball cities with good PinballMap coverage (with approximate coordinates)
TEST_CITIES = [
    ("Portland, OR", 45.5152, -122.6784),
    ("Seattle, WA", 47.6062, -122.3321),
    ("Chicago, IL", 41.8781, -87.6298),
    ("Austin, TX", 30.2672, -97.7431),
    ("Denver, CO", 39.7392, -104.9903),
    ("Los Angeles, CA", 34.0522, -118.2437),
    ("New York, NY", 40.7128, -74.0060),
    ("Boston, MA", 42.3601, -71.0589),
    ("Atlanta, GA", 33.7490, -84.3880),
    ("Phoenix, AZ", 33.4484, -112.0740),
]

CONSOLE_CHANNEL_ID = 888888888


async def setup_test_cities():
    """Set up test cities in the console channel"""
    print("🏙️  Setting up test cities for local development...")

    # Load environment
    load_dotenv(".env.local")

    # Initialize database
    database = Database()

    try:
        with database.get_session() as session:
            # Check if console channel config exists
            channel_config = (
                session.query(ChannelConfig)
                .filter_by(channel_id=CONSOLE_CHANNEL_ID)
                .first()
            )

            if not channel_config:
                print(
                    f"📺 Creating channel config for console channel ({CONSOLE_CHANNEL_ID})"
                )
                channel_config = ChannelConfig(
                    channel_id=CONSOLE_CHANNEL_ID,
                    guild_id=777777777,  # Fake guild ID
                    poll_rate_minutes=60,
                    notification_types="machines",
                    is_active=True,
                )
                session.add(channel_config)
                session.commit()
            else:
                print("📺 Console channel config already exists")

            # Add monitoring targets for each test city
            added_count = 0
            existing_count = 0

            for city_name, latitude, longitude in TEST_CITIES:
                # Check if city already exists
                existing = (
                    session.query(MonitoringTarget)
                    .filter_by(channel_id=CONSOLE_CHANNEL_ID, display_name=city_name)
                    .first()
                )

                if not existing:
                    target = MonitoringTarget(
                        channel_id=CONSOLE_CHANNEL_ID,
                        target_type="geographic",
                        display_name=city_name,
                        latitude=latitude,
                        longitude=longitude,
                        radius_miles=25,
                    )
                    session.add(target)
                    added_count += 1
                    print(f"  ✅ Added: {city_name}")
                else:
                    existing_count += 1
                    print(f"  ⏭️  Already exists: {city_name}")

            session.commit()

            print("\n📊 Summary:")
            print(f"   Added: {added_count} cities")
            print(f"   Already existed: {existing_count} cities")
            print(f"   Total monitoring targets: {added_count + existing_count}")

            # Show current monitoring targets
            all_targets = (
                session.query(MonitoringTarget)
                .filter_by(channel_id=CONSOLE_CHANNEL_ID)
                .all()
            )

            print("\n🎯 Current monitoring targets for console channel:")
            for target in all_targets:
                print(f"   • {target.display_name} ({target.target_type})")

            print("\n🚀 Ready for testing! Start local development with:")
            print("   python src/local_dev.py")
            print("\n   Then test with commands like:")
            print("   > !list")
            print("   > !check")
            print("   > .status")

    except Exception as e:
        print(f"❌ Error setting up test cities: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if not os.path.exists(".env.local"):
        print(
            "❌ .env.local file not found. Please set up local development environment first."
        )
        sys.exit(1)

    asyncio.run(setup_test_cities())
