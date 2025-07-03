"""
Notifier class for sending Discord messages
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from .api import fetch_submissions_for_coordinates, fetch_submissions_for_location
from .database import Database
from .messages import Messages

logger = logging.getLogger(__name__)


class Notifier:
    """Handles formatting and sending messages"""

    def __init__(self, db: Database):
        self.db = db

    async def log_and_send(self, ctx, message: str):
        """Helper method to log and send messages"""
        await ctx.send(message)
        if hasattr(ctx, "author") and hasattr(ctx, "channel"):
            logger.info(
                f"Sent message to {ctx.author.name} ({ctx.author.id}) in channel {ctx.channel.name} ({ctx.channel.id}): {message}"
            )

    def _filter_submissions_by_type(
        self, submissions: List[Dict[str, Any]], notification_type: str
    ) -> List[Dict[str, Any]]:
        """Filter submissions based on notification type."""
        if notification_type == "machines":
            return [
                s
                for s in submissions
                if s.get("submission_type") in ["new_lmx", "remove_machine"]
            ]
        elif notification_type == "comments":
            return [
                s for s in submissions if s.get("submission_type") == "new_condition"
            ]
        return submissions

    async def send_initial_notifications(
        self,
        ctx,
        display_name: str,
        target_type: str,
        location_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_miles: Optional[int] = None,
    ):
        """Fetches and posts initial submissions for a new target."""
        submissions: List[Dict[str, Any]] = []
        try:
            if target_type == "location" and location_id is not None:
                submissions = await fetch_submissions_for_location(
                    location_id=location_id
                )
            elif (
                target_type == "geographic"
                and latitude is not None
                and longitude is not None
            ):
                radius = radius_miles or 25
                submissions = await fetch_submissions_for_coordinates(
                    latitude, longitude, radius
                )
        except Exception as e:
            logger.error(f"Error fetching initial submissions for {display_name}: {e}")
            # Optionally, notify the user that fetching failed.
            # For now, we'll just log and proceed with no submissions.
            submissions = []

        channel_config = self.db.get_channel_config(ctx.channel.id)
        notification_type = (channel_config or {}).get("notification_types", "all")

        filtered_submissions = self._filter_submissions_by_type(
            submissions, notification_type
        )

        latest_submissions = filtered_submissions[:5]

        if latest_submissions:
            await self.log_and_send(
                ctx,
                Messages.Notification.Initial.FOUND.format(
                    count=len(latest_submissions), display_name=display_name
                ),
            )
            await self.post_submissions(ctx, latest_submissions, channel_config)
        else:
            await self.log_and_send(
                ctx,
                Messages.Notification.Initial.NONE.format(display_name=display_name),
            )

    async def post_submissions(
        self,
        ctx,
        submissions: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None,
    ):
        """Post submissions to the channel"""
        # Filter submissions based on notification type
        if config and "notification_types" in config:
            submissions = self._filter_submissions_by_type(
                submissions, config["notification_types"]
            )

        # Skip sleep in test mode
        if not hasattr(ctx, "sent_messages"):
            for submission in submissions:
                message = self.format_submission(submission)
                await self.log_and_send(ctx, message)
                await asyncio.sleep(1)  # Rate limiting only in production
        else:
            # In test mode, send all messages at once
            for submission in submissions:
                message = self.format_submission(submission)
                await self.log_and_send(ctx, message)

    def format_submission(self, submission: Dict[str, Any]) -> str:
        """Format a submission for display"""
        submission_type = submission.get("submission_type", "")
        machine_name = submission.get("machine_name", "Unknown Machine")
        location_name = submission.get("location_name", "Unknown Location")
        user_name = submission.get("user_name", "Anonymous")

        if submission_type == "new_lmx":
            return Messages.Notification.Machine.ADDED.format(
                machine_name=machine_name,
                location_name=location_name,
                user_name=user_name,
            )
        elif submission_type == "remove_machine":
            return Messages.Notification.Machine.REMOVED.format(
                machine_name=machine_name,
                location_name=location_name,
                user_name=user_name,
            )
        elif submission_type == "new_condition":
            comment = submission.get("comment", "")
            comment_text = f"\n💬 {comment}" if comment else ""
            return Messages.Notification.Condition.UPDATED.format(
                machine_name=machine_name,
                location_name=location_name,
                comment_text=comment_text,
                user_name=user_name,
            )
        else:
            return f"📍 **{machine_name}** at **{location_name}** - {submission_type} by {user_name}"
