"""
Simulation Framework Demonstration

This script demonstrates the capabilities of the simulation testing framework
by running various user journeys and showing the results.
"""

import asyncio
import json
import logging
from datetime import datetime

from tests.utils.simulation import SimulationTestFramework, run_complete_user_journey

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_basic_user_journey():
    """Demonstrate a basic user journey."""
    print("\n" + "=" * 60)
    print("DEMO: Basic User Journey")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        print("🤖 Bot simulation framework started")

        # Step 1: Add a location
        print("\n📍 Step 1: Adding Seattle Pinball Museum (ID: 1309)")
        success, messages = await framework.simulate_add_location_by_id(1309)

        print(f"✅ Success: {success}")
        for msg in messages:
            print(f"   Bot: {msg}")

        # Step 2: List targets
        print("\n📋 Step 2: Listing monitoring targets")
        list_messages = await framework.simulate_list_targets()
        for msg in list_messages:
            print(f"   Bot: {msg}")

        # Step 3: Manual check
        print("\n🔍 Step 3: Running manual check")
        check_messages = await framework.simulate_manual_check()
        for msg in check_messages:
            print(f"   Bot: {msg}")

        # Show database state
        print("\n💾 Database State:")
        db_state = framework.get_database_state()
        print(f"   Targets: {len(db_state['targets'])}")
        print(f"   Channel active: {db_state['channels'][0]['is_active']}")
        print(f"   Seen submissions: {len(db_state['seen_submissions'])}")


async def demo_periodic_monitoring():
    """Demonstrate periodic monitoring simulation."""
    print("\n" + "=" * 60)
    print("DEMO: Periodic Monitoring Simulation")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        # Set up monitoring
        print("📍 Setting up location monitoring...")
        await framework.simulate_add_location_by_id(1309)

        # Configure faster polling for demo
        poll_rate = 15  # 15 minutes for demo
        framework.database.update_channel_config(
            framework.test_channel.id,
            framework.test_guild.id,
            poll_rate_minutes=poll_rate,
        )

        print(f"⏰ Configured poll rate: {poll_rate} minutes")
        print("🎬 Starting 45-minute monitoring simulation...")

        # Record start time and messages
        start_time = framework.time_controller.current_time
        initial_messages = len(framework.test_channel.get_sent_messages())

        # Run monitoring simulation
        monitoring_results = await framework.simulate_periodic_monitoring(
            duration_minutes=45, poll_rate_minutes=poll_rate
        )

        # Show results
        end_time = framework.time_controller.current_time
        print(f"⏱️ Simulated time: {start_time} → {end_time}")
        print(f"🔄 Polling cycles: {monitoring_results['polling_cycles']}")
        print(f"💬 New messages: {monitoring_results['message_count']}")

        if monitoring_results["new_messages"]:
            print("\n📢 Messages from monitoring:")
            for msg in monitoring_results["new_messages"]:
                print(f"   Bot: {msg}")
        else:
            print("\n📢 No new notifications (no new submissions detected)")


async def demo_multiple_targets():
    """Demonstrate monitoring multiple targets."""
    print("\n" + "=" * 60)
    print("DEMO: Multiple Target Monitoring")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        targets_added = []

        # Add location
        print("📍 Adding location: Seattle Pinball Museum")
        success, _ = await framework.simulate_add_location_by_id(1309)
        if success:
            targets_added.append("Seattle Pinball Museum")

        # Add coordinates
        print("🗺️ Adding coordinates: Seattle Center area")
        success, _ = await framework.simulate_add_coordinates(47.6062, -122.3321, 5)
        if success:
            targets_added.append("Seattle Center (5mi radius)")

        # Add city
        print("🏙️ Adding city: Seattle, WA")
        success, _ = await framework.simulate_add_city("Seattle, WA", radius=10)
        if success:
            targets_added.append("Seattle, WA (10mi radius)")

        print(f"\n✅ Successfully added {len(targets_added)} targets:")
        for target in targets_added:
            print(f"   • {target}")

        # List all targets
        print("\n📋 Current monitoring configuration:")
        list_messages = await framework.simulate_list_targets()
        for msg in list_messages:
            print(f"   {msg}")

        # Run a check
        print("\n🔍 Running check across all targets:")
        check_messages = await framework.simulate_manual_check()
        for msg in check_messages:
            print(f"   Bot: {msg}")


async def demo_error_handling():
    """Demonstrate error handling capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Error Handling")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        # Test invalid location ID
        print("❌ Testing invalid location ID (999999):")
        success, messages = await framework.simulate_add_location_by_id(999999)
        print(f"   Success: {success}")
        for msg in messages:
            print(f"   Bot: {msg}")

        # Test invalid coordinates
        print("\n❌ Testing invalid coordinates (91, -181):")
        success, messages = await framework.simulate_add_coordinates(91.0, -181.0)
        print(f"   Success: {success}")
        for msg in messages:
            print(f"   Bot: {msg}")

        # Test non-existent city
        print("\n❌ Testing non-existent city:")
        success, messages = await framework.simulate_add_city("NonexistentCity123")
        print(f"   Success: {success}")
        for msg in messages:
            print(f"   Bot: {msg}")


async def demo_message_analysis():
    """Demonstrate message analysis capabilities."""
    print("\n" + "=" * 60)
    print("DEMO: Message Analysis")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        # Add a location and collect messages
        print("📍 Adding location and analyzing responses...")
        success, messages = await framework.simulate_add_location_by_id(1309)

        # Analyze the messages
        analysis = framework.analyze_messages(messages)

        print("\n📊 Message Analysis Results:")
        print(f"   Total messages: {analysis['total_messages']}")
        print(f"   Categories: {analysis['categories']}")
        print(f"   Locations mentioned: {analysis['locations_mentioned']}")
        print(f"   Successes: {len(analysis['successes'])}")
        print(f"   Errors: {len(analysis['errors'])}")

        # Test format validation
        if messages:
            first_message = messages[0]
            print(f"\n🔍 Format Validation for: '{first_message[:50]}...'")

            format_tests = [
                "success_with_name",
                "error_with_reason",
                "list_format",
                "notification",
            ]

            for format_type in format_tests:
                is_valid = framework.validate_message_format(first_message, format_type)
                print(f"   {format_type}: {'✅' if is_valid else '❌'}")


async def demo_api_request_logging():
    """Demonstrate API request logging and verification."""
    print("\n" + "=" * 60)
    print("DEMO: API Request Logging")
    print("=" * 60)

    async with SimulationTestFramework() as framework:
        print("🌐 Performing operations that trigger API calls...")

        # Operations that should trigger different API calls
        await framework.simulate_add_location_by_id(1309)
        await framework.simulate_add_coordinates(47.6062, -122.3321)
        await framework.simulate_add_city("Seattle, WA")

        # Get API logs
        api_logs = framework.api_sim.get_request_logs()

        print("\n📋 PinballMap API Calls:")
        for call in api_logs["pinballmap"]:
            print(f"   {call['timestamp']}: {call['function']} {call['args']}")

        print("\n📋 Geocoding API Calls:")
        for call in api_logs["geocoding"]:
            print(f"   {call['timestamp']}: {call['function']} {call['args']}")

        print(
            f"\n📊 Total API calls: {len(api_logs['pinballmap']) + len(api_logs['geocoding'])}"
        )


async def demo_complete_framework():
    """Demonstrate the complete framework capabilities."""
    print("\n" + "=" * 80)
    print("COMPLETE SIMULATION FRAMEWORK DEMONSTRATION")
    print("=" * 80)

    print("🚀 Running complete user journey with all framework features...")

    # Run the complete journey
    results = await run_complete_user_journey(location_id=1309)

    print("\n📊 COMPLETE JOURNEY RESULTS:")
    print("=" * 40)

    # Show add location results
    add_result = results["add_location"]
    print(f"📍 Add Location: {'✅' if add_result['success'] else '❌'}")
    print(f"   Messages: {len(add_result['messages'])}")

    # Show list results
    list_result = results["list_targets"]
    print(f"📋 List Targets: {len(list_result['messages'])} messages")

    # Show check results
    check_result = results["manual_check"]
    print(f"🔍 Manual Check: {len(check_result['messages'])} messages")

    # Show monitoring results
    monitoring_result = results["monitoring"]
    print(
        f"⏰ Monitoring: {monitoring_result['polling_cycles']} cycles, {monitoring_result['message_count']} new messages"
    )

    # Show summary statistics
    summary = results["summary"]
    framework_info = summary["framework_info"]
    api_logs = summary["api_logs"]

    print("\n🔧 Framework Configuration:")
    print(f"   Realistic timing: {framework_info['use_realistic_timing']}")
    print(f"   Simulation end time: {framework_info['current_time']}")

    print("\n🌐 API Activity:")
    print(f"   PinballMap calls: {len(api_logs['pinballmap'])}")
    print(f"   Geocoding calls: {len(api_logs['geocoding'])}")

    print("\n💾 Database State:")
    db_state = summary["database_state"]
    print(f"   Active channels: {len(db_state['channels'])}")
    print(f"   Monitoring targets: {len(db_state['targets'])}")
    print(f"   Seen submissions: {len(db_state['seen_submissions'])}")

    # Save results to file for inspection
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"simulation_results_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Complete results saved to: {filename}")


async def main():
    """Run all demonstrations."""
    print("🤖 DisPinMap Bot Simulation Framework Demo")
    print("=" * 50)

    demos = [
        ("Basic User Journey", demo_basic_user_journey),
        ("Periodic Monitoring", demo_periodic_monitoring),
        ("Multiple Targets", demo_multiple_targets),
        ("Error Handling", demo_error_handling),
        ("Message Analysis", demo_message_analysis),
        ("API Request Logging", demo_api_request_logging),
        ("Complete Framework", demo_complete_framework),
    ]

    for name, demo_func in demos:
        try:
            print(f"\n🎬 Running: {name}")
            await demo_func()
            print(f"✅ Completed: {name}")
        except Exception as e:
            print(f"❌ Failed: {name} - {e}")
            logger.exception(f"Demo {name} failed")

        # Pause between demos
        await asyncio.sleep(0.5)

    print("\n" + "=" * 50)
    print("🎉 All demonstrations completed!")
    print("=" * 50)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
