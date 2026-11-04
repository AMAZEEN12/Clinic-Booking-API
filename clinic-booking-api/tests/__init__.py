"""Test package. Sets the allowed web origin before the app is imported (see test_cors_api.py)."""

import os

os.environ.setdefault("CORS_ORIGINS", "https://clinic-web.example.test")
