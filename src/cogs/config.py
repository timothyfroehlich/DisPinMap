"""
Cog for configuration-related commands
"""
import logging
from typing import Optional
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

    @commands.command(name='poll_rate')
    async def poll_rate(self, ctx, minutes: int, target_selector: Optional[str] = None):
        """Set poll rate for channel or specific target."""
        try:
            if minutes < 1:
                await self.notifier.log_and_send(ctx, Messages.Command.PollRate.INVALID_RATE)
                return

            if target_selector:
                try:
                    target_id = int(target_selector)
                    targets = self.db.get_monitoring_targets(ctx.channel.id)
                    if not 1 <= target_id <= len(targets):
                        await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_INDEX.format(max_index=len(targets)))
                        return
                    target = targets[target_id - 1]
                    self.db.update_monitoring_target(
                        ctx.channel.id,
                        target['target_type'],
                        target['target_name'],
                        poll_rate_minutes=minutes
                    )
                    await self.notifier.log_and_send(ctx, Messages.Command.PollRate.SUCCESS_TARGET.format(
                        minutes=minutes,
                        target_id=target_id
                    ))
                except ValueError:
                    await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_TARGET_INDEX)
            else:
                self.db.update_channel_config(
                    ctx.channel.id,
                    ctx.guild.id,
                    poll_rate_minutes=minutes
                )
                targets = self.db.get_monitoring_targets(ctx.channel.id)
                for target in targets:
                    if target['poll_rate_minutes'] == self.db.get_channel_config(ctx.channel.id)['poll_rate_minutes']:
                        self.db.update_monitoring_target(
                            ctx.channel.id,
                            target['target_type'],
                            target['target_name'],
                            poll_rate_minutes=minutes
                        )
                await self.notifier.log_and_send(ctx, Messages.Command.PollRate.SUCCESS_CHANNEL.format(minutes=minutes))
        except ValueError:
            await self.notifier.log_and_send(ctx, Messages.Command.PollRate.ERROR)

    @commands.command(name='notifications')
    async def notifications(self, ctx, notification_type: str, target_selector: Optional[str] = None):
        """Set notification type for channel or specific target."""
        valid_types = ['machines', 'comments', 'all']
        if notification_type not in valid_types:
            await self.notifier.log_and_send(ctx, Messages.Command.Notifications.ERROR.format(valid_types=", ".join(valid_types)))
            return

        if target_selector:
            try:
                target_id = int(target_selector)
                targets = self.db.get_monitoring_targets(ctx.channel.id)
                if not 1 <= target_id <= len(targets):
                    await self.notifier.log_and_send(ctx, Messages.Command.Remove.INVALID_INDEX.format(max_index=len(targets)))
                    return
                target = targets[target_id - 1]
                self.db.update_monitoring_target(
                    ctx.channel.id,
                    target['target_type'],
                    target['target_name'],
                    notification_types=notification_type
                )
                await self.notifier.log_and_send(ctx, Messages.Command.Notifications.SUCCESS_TARGET.format(
                    notification_type=notification_type,
                    target_id=target_id
                ))
            except ValueError:
                await self.notifier.log_and_send(ctx, Messages.Command.Remove.ERROR.format(error_message="Invalid target index. Please provide a number."))
        else:
            self.db.update_channel_config(
                ctx.channel.id,
                ctx.guild.id,
                notification_types=notification_type
            )
            targets = self.db.get_monitoring_targets(ctx.channel.id)
            for target in targets:
                if target['notification_types'] == self.db.get_channel_config(ctx.channel.id)['notification_types']:
                    self.db.update_monitoring_target(
                        ctx.channel.id,
                        target['target_type'],
                        target['target_name'],
                        notification_types=notification_type
                    )
            await self.notifier.log_and_send(ctx, Messages.Command.Notifications.SUCCESS_CHANNEL.format(notification_type=notification_type))

async def setup(bot):
    # Ensure dependencies are loaded
    await bot.wait_until_ready()

    database = bot.get_cog("Database")
    if database is None:
        database = Database()

    notifier = bot.get_cog("Notifier")
    if notifier is None:
        notifier = Notifier()

    await bot.add_cog(ConfigCog(bot, database, notifier))
