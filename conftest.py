"""
pytest configuration file
Sets up the Python path to allow importing from src/
"""

import sys
import os

# Add the project root to Python path so 'src' can be imported
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
