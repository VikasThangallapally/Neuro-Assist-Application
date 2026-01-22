try:
    import tensorflow as tf
    print("TensorFlow imported successfully")
except ImportError as e:
    print(f"TensorFlow import failed: {e}")

try:
    import torch
    print("PyTorch imported successfully")
except ImportError as e:
    print(f"PyTorch import failed: {e}")

try:
    from fastapi import FastAPI
    print("FastAPI imported successfully")
except ImportError as e:
    print(f"FastAPI import failed: {e}")

try:
    import uvicorn
    print("Uvicorn imported successfully")
except ImportError as e:
    print(f"Uvicorn import failed: {e}")

try:
    from PIL import Image
    print("PIL imported successfully")
except ImportError as e:
    print(f"PIL import failed: {e}")

try:
    import cv2
    print("OpenCV imported successfully")
except ImportError as e:
    print(f"OpenCV import failed: {e}")

print("Import tests completed.")