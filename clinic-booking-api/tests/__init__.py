"""Test package. Sets the web origin and a very high booking limit before the app is imported.

The high limit stops the shared test run tripping the real limit of 5 a minute; the rate-limit
tests (test_rate_limit_api.py) swap in their own limiter.
"""

import os

os.environ.setdefault("CORS_ORIGINS", "https://clinic-web.example.test")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")
