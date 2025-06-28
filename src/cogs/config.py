"""
Cog for configuration-related commands
"""

import logging
from typing import Optional

import discord
from discord.ext import commands

from src.database import Database
from src.messages import Messages
from src.notifier import Notifier

logger = logging.getLogger(__name__)


class ConfigCog(commands.Cog, name="Configuration"):
    def __init__(self, bot, db: Database, notifier: Notifier):
        self.bot = bot
        self.db = db
        self.notifier = notifier

    @commands.command(
        name="help",
        help="!help [command] - Shows this help message.",
        aliases=["h"],
    )
    async def help_command(self, ctx, *, command_name: Optional[str] = None):
        """Shows a list of all commands or help for a specific command."""
        if command_name:
            command = self.bot.get_command(command_name)
            if command and command.help:
                await ctx.send(f"```\n{command.help}\n```")
            else:
                await ctx.send(f"❌ Command `{command_name}` not found.")
        else:
            embed = discord.Embed(
                title="DisPinMap Bot Help",
                description="I monitor pinball locations from PinballMap.com. Here are my commands:",
                color=discord.Color.blue(),
            )
            for command in sorted(self.bot.commands, key=lambda c: c.name):
                if command.name != "help" and command.help:
                    # Get just the first line of the help text
                    summary = command.help.splitlines()[0]
                    embed.add_field(name=command.name, value=summary, inline=False)
            await ctx.send(embed=embed)

    @commands.command(
        name="poll_rate",
        help="!poll_rate <minutes> [index] - Sets the poll rate.\n\nSets how frequently (in minutes) the bot checks for updates.\nCan be set for the whole channel or for a specific target by its index.",
    )
    async def poll_rate(self, ctx, minutes: str, target_selector: Optional[str] = None):
        """Set poll rate for channel or specific target.

        !poll_rate <minutes> [index] - Sets the poll rate.

        Sets how frequently (in minutes) the bot checks for updates.
        Can be set for the whole channel or for a specific target by its index.
        """
        try:
            minutes_int = int(minutes)
            if minutes_int < 1:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.PollRate.INVALID_RATE
                )
                return

            if target_selector:
                try:
                    target_id = int(target_selector)
                    targets = self.db.get_monitoring_targets(ctx.channel.id)
                    if not 1 <= target_id <= len(targets):
                        await self.notifier.log_and_send(
                            ctx,
                            Messages.Command.Shared.INVALID_INDEX.format(
                                max_index=len(targets)
                            ),
                        )
                        return
                    target = targets[target_id - 1]
                    self.db.update_monitoring_target(
                        ctx.channel.id,
                        target["target_type"],
                        target["target_name"],
                        poll_rate_minutes=minutes_int,
                    )
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.PollRate.SUCCESS_TARGET.format(
                            minutes=minutes_int, target_id=target_id
                        ),
                    )
                except ValueError:
                    await self.notifier.log_and_send(
                        ctx, Messages.Command.Shared.INVALID_INDEX_NUMBER
                    )
            else:
                self.db.update_channel_config(
                    ctx.channel.id, ctx.guild.id, poll_rate_minutes=minutes_int
                )
                targets = self.db.get_monitoring_targets(ctx.channel.id)
                for target in targets:
                    channel_config = self.db.get_channel_config(ctx.channel.id)
                    if (
                        channel_config
                        and target["poll_rate_minutes"]
                        == channel_config["poll_rate_minutes"]
                    ):
                        self.db.update_monitoring_target(
                            ctx.channel.id,
                            target["target_type"],
                            target["target_name"],
                            poll_rate_minutes=minutes_int,
                        )
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.PollRate.SUCCESS_CHANNEL.format(
                        minutes=minutes_int
                    ),
                )
        except ValueError:
            await self.notifier.log_and_send(ctx, Messages.Command.PollRate.ERROR)

    @commands.command(
        name="notifications",
        help="!notifications <type> [index] - Sets notification types.\n\nSets the type of notifications (machines, comments, all).\nCan be set for the whole channel or for a specific target by its index.",
    )
    async def notifications(
        self, ctx, notification_type: str, target_selector: Optional[str] = None
    ):
        """Set notification type for channel or specific target.

        !notifications <type> [index] - Sets notification types.

        Sets the type of notifications (machines, comments, all).
        Can be set for the whole channel or for a specific target by its index.
        """
        valid_types = ["machines", "comments", "all"]
        if notification_type not in valid_types:
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Notifications.ERROR.format(
                    valid_types=", ".join(valid_types)
                ),
            )
            return

        if target_selector:
            try:
                target_id = int(target_selector)
                targets = self.db.get_monitoring_targets(ctx.channel.id)
                if not 1 <= target_id <= len(targets):
                    await self.notifier.log_and_send(
                        ctx,
                        Messages.Command.Shared.INVALID_INDEX.format(
                            max_index=len(targets)
                        ),
                    )
                    return
                target = targets[target_id - 1]
                self.db.update_monitoring_target(
                    ctx.channel.id,
                    target["target_type"],
                    target["target_name"],
                    notification_types=notification_type,
                )
                await self.notifier.log_and_send(
                    ctx,
                    Messages.Command.Notifications.SUCCESS_TARGET.format(
                        notification_type=notification_type, target_id=target_id
                    ),
                )
            except ValueError:
                await self.notifier.log_and_send(
                    ctx, Messages.Command.Shared.INVALID_INDEX_NUMBER
                )
        else:
            self.db.update_channel_config(
                ctx.channel.id, ctx.guild.id, notification_types=notification_type
            )
            targets = self.db.get_monitoring_targets(ctx.channel.id)
            for target in targets:
                channel_config = self.db.get_channel_config(ctx.channel.id)
                if (
                    channel_config
                    and target["notification_types"]
                    == channel_config["notification_types"]
                ):
                    self.db.update_monitoring_target(
                        ctx.channel.id,
                        target["target_type"],
                        target["target_name"],
                        notification_types=notification_type,
                    )
            await self.notifier.log_and_send(
                ctx,
                Messages.Command.Notifications.SUCCESS_CHANNEL.format(
                    notification_type=notification_type
                ),
            )


async def setup(bot):
    """Setup function for Discord.py extension loading"""
    # Get shared instances from bot
    database = getattr(bot, "database", None)
    notifier = getattr(bot, "notifier", None)

    if database is None or notifier is None:
        raise RuntimeError(
            "Database and Notifier must be initialized on bot before loading cogs"
        )

    await bot.add_cog(ConfigCog(bot, database, notifier))
