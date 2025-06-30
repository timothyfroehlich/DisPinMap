"""
Unit tests for the main module.

These tests ensure that the bot creation, configuration, and startup logic
works correctly in both production and testing environments.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.main import (
    cleanup,
    create_bot,
    get_secret,
    handle_health_check,
    handle_signal,
    start_http_server,
)


class TestMainModule:
    """Test the main module functions"""

    @pytest.mark.asyncio
    async def test_create_bot_with_defaults(self):
        """Test creating bot with default parameters"""
        bot = await create_bot()

        assert bot is not None
        assert hasattr(bot, "database")
        assert hasattr(bot, "notifier")
        assert bot.command_prefix == "!"

    @pytest.mark.asyncio
    async def test_create_bot_with_injected_dependencies(self):
        """Test creating bot with injected dependencies"""
        # Create a proper mock session factory that can be subscripted
        mock_session_factory = Mock()
        mock_session_factory.kw = {"bind": Mock()}
        mock_notifier = Mock()

        bot = await create_bot(
            db_session_factory=mock_session_factory, notifier=mock_notifier
        )

        assert bot is not None
        assert bot.database is not None
        assert bot.notifier == mock_notifier

    @pytest.mark.asyncio
    async def test_create_bot_with_notifier_none(self):
        """Test creating bot with notifier=None (should create new notifier)"""
        bot = await create_bot(notifier=None)

        assert bot is not None
        assert hasattr(bot, "notifier")
        assert bot.notifier is not None

    @pytest.mark.asyncio
    async def test_create_bot_cog_loading_error(self):
        """Test bot creation when cog loading fails"""
        with patch("os.listdir") as mock_listdir:
            mock_listdir.return_value = ["test_cog.py"]

            with patch("src.main.create_bot") as mock_create_bot:
                mock_bot = Mock()
                mock_bot.load_extension = AsyncMock()
                mock_bot.load_extension.side_effect = Exception("Cog loading failed")
                mock_create_bot.return_value = mock_bot

                bot = await create_bot()

                assert bot is not None
                # Should continue even if cog loading fails

    def test_get_secret_success(self):
        """Test successful secret retrieval"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.payload.data = b"test_secret"
        mock_client.access_secret_version.return_value = mock_response

        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient",
            return_value=mock_client,
        ):
            result = get_secret("test_secret", "test_project")

            assert result == "test_secret"
            mock_client.access_secret_version.assert_called_once()

    def test_get_secret_import_error(self):
        """Test secret retrieval when google-cloud-secret-manager is not installed"""
        import builtins

        original_import = builtins.__import__

        def import_side_effect(name, *args, **kwargs):
            if name == "google.cloud.secretmanager":
                raise ImportError()
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_side_effect):
            result = get_secret("test_secret", "test_project")
            assert result is None

    def test_get_secret_exception(self):
        """Test secret retrieval when an exception occurs"""
        mock_client = Mock()
        mock_client.access_secret_version.side_effect = Exception(
            "Secret access failed"
        )

        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient",
            return_value=mock_client,
        ):
            result = get_secret("test_secret", "test_project")

            assert result is None

    @pytest.mark.asyncio
    async def test_handle_health_check(self):
        """Test health check endpoint"""
        mock_request = Mock()

        response = await handle_health_check(mock_request)

        assert response.status == 200
        assert response.text == "OK"

    @pytest.mark.asyncio
    async def test_start_http_server(self):
        """Test HTTP server startup"""
        with patch("os.getenv", return_value="8080"):
            with patch("aiohttp.web.AppRunner") as mock_runner_class:
                mock_runner = Mock()
                mock_runner.setup = AsyncMock()
                mock_runner.cleanup = AsyncMock()
                mock_runner_class.return_value = mock_runner

                with patch("aiohttp.web.TCPSite") as mock_site_class:
                    mock_site = Mock()
                    mock_site.start = AsyncMock()
                    mock_site_class.return_value = mock_site

                    runner = await start_http_server()

                    assert runner is not None
                    # Clean up
                    await runner.cleanup()

    @pytest.mark.asyncio
    async def test_start_http_server_custom_port(self):
        """Test HTTP server startup with custom port"""
        with patch("os.getenv", return_value="9000"):
            with patch("aiohttp.web.AppRunner") as mock_runner_class:
                mock_runner = Mock()
                mock_runner.setup = AsyncMock()
                mock_runner.cleanup = AsyncMock()
                mock_runner_class.return_value = mock_runner

                with patch("aiohttp.web.TCPSite") as mock_site_class:
                    mock_site = Mock()
                    mock_site.start = AsyncMock()
                    mock_site_class.return_value = mock_site

                    runner = await start_http_server()

                    assert runner is not None
                    # Clean up
                    await runner.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_with_http_runner(self):
        """Test cleanup with HTTP runner"""
        mock_bot = Mock()
        mock_bot.is_closed.return_value = False
        mock_bot.close = AsyncMock()

        mock_runner = Mock()
        mock_runner.cleanup = AsyncMock()

        # Set global http_runner
        import src.main

        src.main.http_runner = mock_runner

        await cleanup(mock_bot)

        mock_runner.cleanup.assert_called_once()
        mock_bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_without_http_runner(self):
        """Test cleanup without HTTP runner"""
        mock_bot = Mock()
        mock_bot.is_closed.return_value = False
        mock_bot.close = AsyncMock()

        # Set global http_runner to None
        import src.main

        src.main.http_runner = None

        await cleanup(mock_bot)

        mock_bot.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_bot_already_closed(self):
        """Test cleanup when bot is already closed"""
        mock_bot = Mock()
        mock_bot.is_closed.return_value = True
        mock_bot.close = AsyncMock()

        # Set global http_runner to None
        import src.main

        src.main.http_runner = None

        await cleanup(mock_bot)

        mock_bot.close.assert_not_called()

    def test_handle_signal(self):
        """Test signal handler"""
        mock_bot = Mock()

        with patch("asyncio.create_task") as mock_create_task:
            handle_signal(2, None, mock_bot)  # SIGINT

            mock_create_task.assert_called_once()

    def test_test_startup_flag(self):
        """Test TEST_STARTUP flag detection"""
        # This tests the global flag that's set based on sys.argv
        # We can't easily test this without modifying sys.argv, so just verify it exists
        from src.main import TEST_STARTUP

        assert isinstance(TEST_STARTUP, bool)

    @pytest.mark.asyncio
    async def test_error_handler_missing_required_argument(self):
        """Test that the error handler message exists and is properly formatted"""
        from src.messages import Messages

        # Test that the new error message exists and is properly formatted
        missing_index_msg = Messages.Command.Remove.MISSING_INDEX
        assert missing_index_msg is not None
        assert "❌" in missing_index_msg
        assert "!rm <index>" in missing_index_msg
        assert "!list" in missing_index_msg

        # This verifies that our error message integration point exists
        # The actual Discord.py integration is tested in integration tests
