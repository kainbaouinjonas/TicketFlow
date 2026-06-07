import sys
import os
from pathlib import Path

# Add the apps/ directory to sys.path so Django app modules can be imported directly
# (e.g., `from events.models import ...` instead of `from apps.events.models import ...`)
BASE_DIR = Path(__file__).resolve().parent
apps_dir = str(BASE_DIR / 'apps')
if apps_dir not in sys.path:
    sys.path.insert(0, apps_dir)
