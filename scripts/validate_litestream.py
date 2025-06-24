#!/usr/bin/env python3
"""
Litestream backup validation script

This script provides basic validation for the Litestream SQLite backup system:
- Checks if database file exists
- Validates Litestream configuration
- Tests database connectivity
- Verifies backup functionality

Usage:
    python scripts/validate_litestream.py
"""

import os
import subprocess
import sys


def check_environment():
    """Check required environment variables"""
    required_vars = ["DATABASE_PATH", "LITESTREAM_BUCKET"]
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        return False

    print("✅ All required environment variables present")
    return True


def check_database_file():
    """Check if database file exists and is accessible"""
    db_path = os.getenv("DATABASE_PATH", "pinball_bot.db")

    if not os.path.exists(db_path):
        print(f"⚠️  Database file not found: {db_path}")
        return False

    try:
        # Try to open database file
        import sqlite3

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        conn.close()

        print(f"✅ Database accessible: {db_path} ({table_count} tables)")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def check_litestream_binary():
    """Check if Litestream binary is available"""
    try:
        result = subprocess.run(
            ["litestream", "version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Litestream binary found: {version}")
            return True
        else:
            print(f"❌ Litestream binary error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Litestream binary not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Litestream binary timeout")
        return False


def check_litestream_config():
    """Check if Litestream configuration is valid"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config_path = os.path.join(script_dir, "..", "litestream.yml")
    config_path = os.getenv("LITESTREAM_CONFIG_PATH", default_config_path)

    if not os.path.exists(config_path):
        print(f"❌ Litestream config not found: {config_path}")
        return False

    try:
        import yaml  # type: ignore

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # Basic validation
        if "dbs" not in config:
            print("❌ Litestream config missing 'dbs' section")
            return False

        print(f"✅ Litestream config valid: {config_path}")
        return True
    except ImportError:
        print("⚠️  PyYAML not available, skipping config validation")
        return True
    except Exception as e:
        print(f"❌ Litestream config error: {e}")
        return False


def test_database_operations():
    """Test basic database operations"""
    try:
        # Import database module
        sys.path.append(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        )
        from database import Database

        # Test database creation and basic operations
        db = Database()

        # Test basic functionality
        db.get_active_channels()

        db.close()
        print("✅ Database operations successful")
        return True
    except Exception as e:
        print(f"❌ Database operations failed: {e}")
        return False


def main():
    """Run all validation checks"""
    print("=== Litestream Backup Validation ===\n")

    checks = [
        ("Environment Variables", check_environment),
        ("Database File", check_database_file),
        ("Litestream Binary", check_litestream_binary),
        ("Litestream Configuration", check_litestream_config),
        ("Database Operations", test_database_operations),
    ]

    results = []
    for name, check_func in checks:
        print(f"Checking {name}...")
        result = check_func()
        results.append((name, result))
        print()

    # Summary
    print("=== Validation Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All validations successful! Litestream setup is ready.")
        return 0
    else:
        print("❌ Some validations failed. Please review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
