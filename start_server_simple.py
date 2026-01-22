#!/usr/bin/env python
"""Simple server starter for FastAPI app"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Brain MRI Validation System - Backend Server")
print("=" * 60)
print()

try:
    print("[1/3] Importing FastAPI dependencies...")
    import uvicorn
    print("      ✓ uvicorn imported")
    
    import fastapi
    print("      ✓ fastapi imported")
    
    from PIL import Image
    print("      ✓ PIL imported")
    
    import numpy as np
    print("      ✓ numpy imported")
    
    print()
    print("[2/3] Loading FastAPI app...")
    from fastapi_app import app
    print("      ✓ FastAPI app loaded")
    
    print()
    print("[3/3] Starting server...")
    print("      Listening on: http://0.0.0.0:8000")
    print("      Local URL:    http://localhost:8000")
    print("      API Docs:     http://localhost:8000/docs")
    print()
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
except ImportError as e:
    print(f"❌ ERROR: Missing dependency: {e}")
    print()
    print("Please install required packages:")
    print("  pip install uvicorn fastapi pillow numpy")
    sys.exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)
