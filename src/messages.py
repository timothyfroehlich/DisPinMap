"""
Centralized message system for user-facing messages.

This module provides a type-safe, centralized location for all user-facing messages
used throughout the application. Messages are organized in a hierarchical structure
matching their usage context.
"""

# from typing import Any, Dict, List, Optional


class Messages:
    """Base class for all user-facing messages."""

    class Command:
        """Command-related messages."""

        class Add:
            """Messages for the add command."""

            SUCCESS = "✅ Added {target_type}: **{name}** - Monitoring started!"
            """Format parameters:
            - target_type: str - Type of target (location, coordinates, city)
            - name: str - Name or identifier of the target
            """

            ERROR = "❌ Error adding {target_type}: {error_message}"
            """Format parameters:
            - target_type: str - Type of target (location, coordinates, city)
            - error_message: str - Error message to display
            """

            INVALID_TYPE = "❌ Invalid target type"
            """No format parameters."""

            NO_LOCATIONS = "❌ No locations found matching '{search_term}'"
            """Format parameters:
            - search_term: str - The search term that was used
            """

            SUGGESTIONS = "Location '{search_term}' not found directly. Did you mean one of these?\n{suggestions}\n\nPlease use `/add location <ID>` with the ID of the correct location."
            """Format parameters:
            - search_term: str - The search term that was used
            - suggestions: str - List of suggested locations
            """

            LOCATION_SUGGESTIONS = "Location '{search_term}' not found directly. Did you mean one of these?\n{suggestions}\n\nPlease use `/add location <ID>` with the ID of the correct location."
            """Format parameters:
            - search_term: str - The search term that was used
            - suggestions: str - List of suggested locations
            """

            CITY_SUGGESTIONS = "Multiple cities found for '{city_name}'. Please be more specific:\n{suggestions}"
            """Format parameters:
            - city_name: str - The city name that was searched
            - suggestions: str - List of suggested city names
            """

            INVALID_COORDS = "❌ Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180"
            """No format parameters."""

            INVALID_RADIUS = "❌ Radius must be between 1 and 100 miles"
            """No format parameters."""

            MISSING_LOCATION = "❌ Please provide a location name or ID. Usage: `/add location <name_or_id>`"
            MISSING_COORDS = "❌ Please provide latitude and longitude. Usage: `/add coordinates <lat> <lon> [radius]`"
            INVALID_COORDS_FORMAT = (
                "❌ Invalid coordinates. Please provide valid numbers."
            )
            MISSING_CITY = (
                "❌ Please provide a city name. Usage: `/add city <name> [radius]`"
            )

            LOCATION_NOT_FOUND = "❌ Location ID {location_id} not found. Please check the ID on PinballMap.com."
            """Format parameters:
            - location_id: int - The location ID that was not found
            """

            CITY_NOT_FOUND = "❌ Could not find coordinates for city: {city_name}"
            """Format parameters:
            - city_name: str - The city name that was not found
            """

            NO_RESULTS = "❌ No results found for: {search_term}"
            """Format parameters:
            - search_term: str - The search term that yielded no results
            """

            INVALID_INDEX = (
                "❌ Invalid index. Please use a number between 1 and {max_index}"
            )
            """Format parameters:
            - max_index: int - Maximum valid index
            """

            INVALID_INDEX_NUMBER = "❌ Please provide a valid number for the index"
            """No format parameters."""

            INVALID_TARGET_INDEX = "❌ Invalid target index. Please provide a number."
            """No format parameters."""

        class Remove:
            """Messages for the remove command."""

            SUCCESS = "✅ Removed {target_type}: **{name}**"
            """Format parameters:
            - target_type: str - Type of target (location, coordinates, city)
            - name: str - Name or identifier of the target
            """

            ERROR = "❌ {error_message}"
            """Format parameters:
            - error_message: str - Error message to display
            """

            NO_TARGETS = "❌ No targets to remove. Use `/list` to see current targets."
            """No format parameters."""

            INVALID_INDEX = (
                "❌ Invalid index. Please use a number between 1 and {max_index}"
            )
            """Format parameters:
            - max_index: int - Maximum valid index
            """

            INVALID_INDEX_NUMBER = "❌ Please provide a valid number for the index"
            """No format parameters."""

            INVALID_TARGET_INDEX = "❌ Invalid target index. Please provide a number."
            """No format parameters."""

        class TargetList:
            """Messages for the list command."""

            NO_TARGETS = "No targets being monitored. Use `/add` to add some."
            """No format parameters."""

            HEADER = "**Monitored Targets:**\n{targets}\n\n**Channel Defaults:**\nPoll Rate: {poll_rate} minutes\nNotifications: {notification_types}\n\nUse `/rm <index>` to remove a target"
            """Format parameters:
            - targets: str - List of monitored targets
            - poll_rate: int - Channel's poll rate in minutes
            - notification_types: str - Channel's notification types
            """

        class Export:
            """Messages for the export command."""

            NO_TARGETS = "No targets to export. Use `/add` to add some first."
            """No format parameters."""

            HEADER = "**Export Commands:**\n```\n{commands}\n```"
            """Format parameters:
            - commands: str - List of commands to export
            """

        class PollRate:
            """Messages for the poll rate command."""

            SUCCESS_TARGET = (
                "✅ Set poll rate to {minutes} minutes for target {target_id}"
            )
            """Format parameters:
            - minutes: int - Poll rate in minutes
            - target_id: int - Target index
            """

            SUCCESS_CHANNEL = (
                "✅ Set default poll rate to {minutes} minutes for all targets"
            )
            """Format parameters:
            - minutes: int - Poll rate in minutes
            """

            ERROR = "❌ Please provide a valid number of minutes"
            """No format parameters."""

            INVALID_RATE = "❌ Poll rate must be at least 1 minute"
            """No format parameters."""

        class Notifications:
            """Messages for the notifications command."""

            SUCCESS_TARGET = (
                "✅ Set notifications to {notification_type} for target {target_id}"
            )
            """Format parameters:
            - notification_type: str - Type of notifications (machines, comments, all)
            - target_id: int - Target index
            """

            SUCCESS_CHANNEL = (
                "✅ Set default notifications to {notification_type} for all targets"
            )
            """Format parameters:
            - notification_type: str - Type of notifications (machines, comments, all)
            """

            ERROR = "❌ Invalid notification type. Use: {valid_types}"
            """Format parameters:
            - valid_types: str - Comma-separated list of valid notification types
            """

        class Error:
            """Error messages."""

            COMMAND = "❌ An unexpected error occurred while running `/{command}`. Please check the logs or contact the admin."
            """Format parameters:
            - command: str - Name of the command that failed
            """

            GENERAL = "❌ An unexpected error occurred: {error}"
            """Format parameters:
            - error: str - Error message
            """

        class Status:
            """Status command messages."""

            NO_TARGETS = "No monitoring targets configured for this channel. Use `/add` to add a target."
            """No format parameters."""

            NO_TARGETS_TO_CHECK = "No targets to check for this channel. Use `/add` to add some targets first."
            """No format parameters."""

    class Notification:
        """Notification-related messages."""

        class Machine:
            """Machine-related notifications."""

            ADDED = "🎮 **{machine_name}** added at **{location_name}** by {user_name}"
            """Format parameters:
            - machine_name: str - Name of the machine
            - location_name: str - Name of the location
            - user_name: str - Name of the user who added it
            """

            REMOVED = (
                "🗑️ **{machine_name}** removed from **{location_name}** by {user_name}"
            )
            """Format parameters:
            - machine_name: str - Name of the machine
            - location_name: str - Name of the location
            - user_name: str - Name of the user who removed it
            """

            MULTIPLE_ADDED = (
                "🎮 **{count} New Pinball Machines Added!**\n{machines}{remaining_text}"
            )
            """Format parameters:
            - count: int - Number of machines added
            - machines: str - List of machines added
            - remaining: int - Number of additional machines not shown
            """

            MULTIPLE_REMOVED = (
                "🗑️ **{count} Pinball Machines Removed:**\n{machines}{remaining_text}"
            )
            """Format parameters:
            - count: int - Number of machines removed
            - machines: str - List of machines removed
            - remaining: int - Number of additional machines not shown
            """

            REMAINING_MACHINES = "... and {count} more machines"
            """Format parameters:
            - count: int - Number of additional machines not shown
            """

        class Condition:
            """Condition-related notifications."""

            UPDATED = "🔧 **{machine_name}** at **{location_name}**{comment_text} - by {user_name}"
            """Format parameters:
            - machine_name: str - Name of the machine
            - location_name: str - Name of the location
            - comment: str - Condition update comment
            - user_name: str - Name of the user who updated it
            """

        class Initial:
            """Initial notification messages."""

            FOUND = "Found {count} recent submissions for {target_type}:"
            """Format parameters:
            - count: int - Number of submissions found
            - target_type: str - Type of target being monitored
            """

            NONE = "No recent submissions found for {target_type}"
            """Format parameters:
            - target_type: str - Type of target being monitored
            """

    class System:
        """System-related messages."""

        class Error:
            """Error messages."""

            UNEXPECTED = "❌ An unexpected error occurred while running the command"
            """Format parameters:
            - error: str - Error message
            """

            RESPONSE_MISSING_FIELD = "Response missing '{field}' field"
            """Format parameters:
            - field: str - Name of the missing field
            """

            DATA_MISSING_FIELD = "{data_type} data missing '{field}' field"
            """Format parameters:
            - data_type: str - Type of data (e.g., "Location", "Submission")
            - field: str - Name of the missing field
            """

            INVALID_TIMESTAMP = "Invalid timestamp format: {timestamp}"
            """Format parameters:
            - timestamp: str - The invalid timestamp string
            """

            INVALID_COORDINATE_TYPE = (
                "Invalid {coord_type} type: expected number, got {type}"
            )
            """Format parameters:
            - coord_type: str - Type of coordinate ("Latitude" or "Longitude")
            - type: type - Actual type received
            """
