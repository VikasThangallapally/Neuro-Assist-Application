import os
import json
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from PIL import Image
import numpy as np

# Load model and labels
model = None
labels = {}

if os.path.exists('models/model.h5'):
    model = tf.keras.models.load_model('models/model.h5')

if os.path.exists('models/labels.json'):
    with open('models/labels.json', 'r') as f:
        labels = json.load(f)

def predict_image(img_path):
    if model is None:
        return "Model not loaded", 0.0
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0

    predictions = model.predict(img_array)
    predicted_class = np.argmax(predictions, axis=1)[0]
    confidence = np.max(predictions)
    label = labels.get(str(predicted_class), f"Class {predicted_class}")

    return label, confidence

# Path to testing folder
testing_path = 'brain tumor/Testing'

results = {}

if os.path.exists(testing_path):
    for folder in os.listdir(testing_path):
        folder_path = os.path.join(testing_path, folder)
        if os.path.isdir(folder_path):
            results[folder] = []
            for img_file in os.listdir(folder_path):
                if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(folder_path, img_file)
                    label, conf = predict_image(img_path)
                    results[folder].append({
                        'image': img_file,
                        'predicted_label': label,
                        'confidence': float(conf)
                    })
                    print(f"{folder}/{img_file}: {label} ({conf:.4f})")

# Save results to JSON
with open('testing_predictions.json', 'w') as f:
    json.dump(results, f, indent=4)

print("Predictions saved to testing_predictions.json")