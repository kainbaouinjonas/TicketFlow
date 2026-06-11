import sys
import os
import pytest
from pathlib import Path

# Add the apps/ directory to sys.path so Django app modules can be imported directly
# (e.g., `from events.models import ...` instead of `from apps.events.models import ...`)
BASE_DIR = Path(__file__).resolve().parent
apps_dir = str(BASE_DIR / 'apps')
if apps_dir not in sys.path:
    sys.path.insert(0, apps_dir)

@pytest.fixture(autouse=True)
def enable_celery_eager_mode(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_RESULT_BACKEND = 'cache+memory://'
    settings.CELERY_BROKER_URL = 'memory://'

