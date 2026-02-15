"""
High-level simulation tests for key user journeys.

These tests simulate a user's entire interaction with the bot over a series
of steps, verifying that the system as a whole behaves as expected.

The original tests here were pure database CRUD operations that didn't test
any user-facing behavior. They have been replaced by proper integration tests
in tests/integration/test_monitoring_cycle.py which exercise the full
Runner → Database → Notifier → API pipeline.
"""
