import os
import tensorflow as tf

# Check if model exists and loads
model_path = 'models/model.h5'
if os.path.exists(model_path):
    try:
        model = tf.keras.models.load_model(model_path)
        print("Model loaded successfully.")
        print("Model summary:")
        model.summary()
    except Exception as e:
        print(f"Failed to load model: {e}")
else:
    print("Model file not found.")

# Check labels
labels_path = 'models/labels.json'
if os.path.exists(labels_path):
    import json
    with open(labels_path, 'r') as f:
        labels = json.load(f)
    print("Labels loaded:", labels)
else:
    print("Labels file not found.")