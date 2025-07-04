#!/usr/bin/env python3
"""
Download production database from GCS backup for local development
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def setup_logging():
    """Set up logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def restore_litestream_backup(bucket_name: str, local_path: str) -> bool:
    """Restore database from Litestream backup in GCS bucket"""
    logger = logging.getLogger(__name__)
    
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Create a temporary litestream configuration for restoration
        litestream_config = f"""
dbs:
  - path: {local_path}
    replicas:
      - url: gcs://{bucket_name}/db-v2
"""
        
        config_path = "litestream_restore.yml"
        with open(config_path, 'w') as f:
            f.write(litestream_config)
        
        logger.info(f"Restoring database from Litestream backup in bucket: {bucket_name}")
        logger.info(f"Target path: {local_path}")
        
        # Use litestream restore command
        result = subprocess.run([
            'litestream', 'restore', '-config', config_path, local_path
        ], capture_output=True, text=True)
        
        # Clean up config file
        os.remove(config_path)
        
        if result.returncode != 0:
            logger.error(f"Litestream restore failed: {result.stderr}")
            return False
        
        logger.info(f"Successfully restored database to {local_path}")
        logger.info(f"Litestream output: {result.stdout}")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}")
        return False

def verify_database(db_path: str) -> bool:
    """Verify the downloaded database is valid"""
    logger = logging.getLogger(__name__)
    
    try:
        import sqlite3
        
        # Check if file exists and is not empty
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            return False
        
        if os.path.getsize(db_path) == 0:
            logger.error(f"Database file is empty: {db_path}")
            return False
        
        # Try to open the database and run a simple query
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if basic tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        logger.info(f"Database contains {len(tables)} tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            logger.info(f"  - {table[0]}: {count} rows")
        
        conn.close()
        logger.info("Database verification successful")
        return True
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False

def main():
    """Main function"""
    logger = setup_logging()
    
    # Configuration
    bucket_name = "dispinmap-bot-sqlite-backups"
    local_path = "local_db/pinball_bot.db"
    
    logger.info("=== Production Database Download ===")
    logger.info(f"Bucket: {bucket_name}")
    logger.info(f"Local path: {local_path}")
    
    # Check if database already exists
    if os.path.exists(local_path):
        response = input(f"Database already exists at {local_path}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            logger.info("Cancelled by user")
            return 1
    
    # Restore the backup using Litestream
    if not restore_litestream_backup(bucket_name, local_path):
        logger.error("Failed to restore database")
        return 1
    
    # Verify the download
    if not verify_database(local_path):
        logger.error("Database verification failed")
        return 1
    
    logger.info("✅ Database download and verification complete!")
    logger.info(f"Database is ready at: {local_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())