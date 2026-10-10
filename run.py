"""
Main entry point to run RideWise Assist FastAPI server.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting RideWise Assist server on http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=False
    )
