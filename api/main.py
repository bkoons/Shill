# Vercel Serverless Function Entry Point
# This file must be at api/index.py for Vercel to detect it as a Python serverless function

import sys
import os

# Add backend to path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.main import app

# Vercel expects the ASGI app to be named `app` or `handler`
# FastAPI app is already named `app` in backend/main.py