#!/usr/bin/env python
"""Test script to diagnose prediction issues"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Brain MRI Validation System - Diagnostics")
print("=" * 60)
print()

# Check dependencies
print("[1] Checking dependencies...")
dependencies = {
    'fastapi': 'FastAPI',
    'uvicorn': 'Uvicorn',
    'PIL': 'Pillow',
    'numpy': 'NumPy',
    'cv2': 'OpenCV',
    'tensorflow': 'TensorFlow',
    'sklearn': 'Scikit-Learn',
}

missing = []
for module, name in dependencies.items():
    try:
        __import__(module)
        print(f"  ✓ {name}")
    except ImportError:
        print(f"  ✗ {name} - MISSING")
        missing.append(name)

print()

if missing:
    print(f"[2] Missing dependencies: {', '.join(missing)}")
    print()
    print("Install with:")
    print(f"  pip install {' '.join([d.lower() for d in missing])}")
    sys.exit(1)

print("[2] All dependencies installed ✓")
print()

# Check model files
print("[3] Checking model files...")
model_path = 'models/model_selected.h5'
labels_path = 'models/labels.json'

if os.path.exists(model_path):
    print(f"  ✓ Model file exists: {model_path}")
else:
    print(f"  ✗ Model file missing: {model_path}")
    
if os.path.exists(labels_path):
    print(f"  ✓ Labels file exists: {labels_path}")
else:
    print(f"  ✗ Labels file missing: {labels_path}")

print()

# Try loading the model
print("[4] Testing model loading...")
try:
    import tensorflow as tf
    model = tf.keras.models.load_model(model_path)
    print(f"  ✓ Model loaded successfully")
    print(f"    Input shape: {model.inputs[0].shape}")
    print(f"    Output shape: {model.outputs[0].shape}")
except Exception as e:
    print(f"  ✗ Error loading model: {e}")
    sys.exit(1)

print()
print("[5] Testing image processing...")
try:
    from PIL import Image
    import numpy as np
    
    # Create a test image (256x256 grayscale)
    test_img = Image.new('L', (256, 256), color=128)
    arr = np.array(test_img).astype('float32') / 255.0
    batched = np.expand_dims(arr, axis=0)
    
    print(f"  ✓ Test image created: {test_img.size}")
    print(f"  ✓ Preprocessed shape: {batched.shape}")
    
    # Try prediction
    pred = model.predict(batched, verbose=0)
    print(f"  ✓ Prediction successful")
    print(f"    Output shape: {pred.shape}")
    print(f"    Predicted class: {np.argmax(pred[0])}")
    print(f"    Confidence: {np.max(pred[0]):.2%}")
    
except Exception as e:
    print(f"  ✗ Error in image processing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("✓ All diagnostics passed! System is ready.")
print("=" * 60)
