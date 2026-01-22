import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import json

# Load model
model_path = 'models/model.h5'
if os.path.exists(model_path):
    model = tf.keras.models.load_model(model_path)
    print("Model loaded successfully.")
else:
    print("Model not found.")
    exit()

# Load labels
labels_path = 'models/labels.json'
if os.path.exists(labels_path):
    with open(labels_path, 'r') as f:
        labels = json.load(f)
    class_names = {v: k for k, v in labels.items()}
else:
    print("Labels not found.")
    exit()

# Function to predict
def predict_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0

    predictions = model.predict(img_array)
    predicted_class = np.argmax(predictions, axis=1)[0]
    confidence = np.max(predictions)

    return class_names[predicted_class], confidence

# Test on a sample image (assuming there's a test image)
test_image = 'scripts/sample_image.jpg'  # Adjust path as needed
if os.path.exists(test_image):
    label, conf = predict_image(test_image)
    print(f"Predicted: {label} with confidence {conf:.2f}")
else:
    print("Test image not found. Please provide a valid image path.")

print("Prediction test completed.")