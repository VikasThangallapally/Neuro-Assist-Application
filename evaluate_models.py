import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import json

# Load model
model_path = 'models/model.h5'
if os.path.exists(model_path):
    model = tf.keras.models.load_model(model_path)
    print("Model loaded successfully.")
else:
    print("Model not found.")
    exit()

# Data directory
test_dir = 'brain tumor/Testing'

# Image parameters
img_height, img_width = 224, 224
batch_size = 32

# Test data generator
test_datagen = ImageDataGenerator(rescale=1./255)

test_generator = test_datagen.flow_from_directory(
    test_dir,
    target_size=(img_height, img_width),
    batch_size=batch_size,
    class_mode='categorical',
    shuffle=False
)

# Evaluate model
loss, accuracy = model.evaluate(test_generator)
print(f"Test Loss: {loss:.4f}")
print(f"Test Accuracy: {accuracy:.4f}")

# Save evaluation results
results = {
    'test_loss': loss,
    'test_accuracy': accuracy
}

with open('models/eval_results.json', 'w') as f:
    json.dump(results, f)

print("Model evaluation completed.")