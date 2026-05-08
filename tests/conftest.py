"""
Pytest configuration and fixtures.
Adds the project root to sys.path so that core and utils modules can be imported.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
