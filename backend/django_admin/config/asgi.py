"""ASGI config for DHAN Admin project."""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

base_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
