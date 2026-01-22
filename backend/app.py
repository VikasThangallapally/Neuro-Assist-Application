import gradio as gr
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from PIL import Image
import json
import os
import cv2
import re

# Load model and labels
model = None
labels = {}

model_path = None
# Prefer explicitly selected model, otherwise fall back to model.h5
if os.path.exists('models/model_selected.h5'):
    model_path = 'models/model_selected.h5'
elif os.path.exists('models/model.h5'):
    model_path = 'models/model.h5'

if model_path:
    model = tf.keras.models.load_model(model_path)
    print(f'Loaded TF model from {model_path}')

if os.path.exists('models/labels.json'):
    with open('models/labels.json', 'r') as f:
        labels = json.load(f)

# Import chat functions
try:
    from chatbot import chat_response
except ImportError:
    def chat_response(message, last_pred=None, last_conf=None):
        return "Chat not available."

# Prediction function
def _is_grayscale_like(pil: Image.Image) -> bool:
    """Check if the image is mostly grayscale (low color variance)."""
    try:
        arr = np.array(pil.resize((128, 128)))
        if arr.ndim == 2:
            return True
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        diff_rg = np.abs(r.astype(float) - g.astype(float)).mean()
        diff_rb = np.abs(r.astype(float) - b.astype(float)).mean()
        diff_gb = np.abs(g.astype(float) - b.astype(float)).mean()
        # Stricter color variation check for medical images
        return diff_rg < 30 and diff_rb < 30 and diff_gb < 30
    except Exception:
        return False

def _analyze_image_texture(pil: Image.Image) -> dict:
    """Analyze image texture characteristics typical of medical imaging."""
    try:
        gray = pil.convert('L').resize((256, 256))
        arr = np.array(gray).astype('float32')

        # Basic statistics
        mean_val = np.mean(arr)
        std_val = np.std(arr)
        median_val = np.median(arr)

        # Edge detection using simple gradient
        gx = np.gradient(arr, axis=1)
        gy = np.gradient(arr, axis=0)
        gradient_magnitude = np.sqrt(gx**2 + gy**2)
        edge_strength = np.mean(gradient_magnitude)

        # Check for medical imaging patterns
        hist, bins = np.histogram(arr.ravel(), bins=256, range=(0, 255))
        hist_norm = hist / hist.sum()

        low_intensities = hist_norm[0:64].sum()
        mid_intensities = hist_norm[64:192].sum()
        high_intensities = hist_norm[192:256].sum()

        noise_estimate = np.std(gradient_magnitude)

        return {
            'mean': mean_val,
            'std': std_val,
            'median': median_val,
            'edge_strength': edge_strength,
            'low_intensities': low_intensities,
            'mid_intensities': mid_intensities,
            'high_intensities': high_intensities,
            'noise_estimate': noise_estimate
        }
    except Exception:
        return {}

def _detect_brain_structures(pil: Image.Image) -> bool:
    """Check for brain-like anatomical structures."""
    try:
        gray = pil.convert('L').resize((256, 256))
        arr = np.array(gray)

        edges = cv2.Canny(arr, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        circular_contours = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)

            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                if 0.3 < circularity < 0.9 and area > 100:
                    circular_contours += 1

        return circular_contours >= 2

    except Exception:
        return False

def _is_brain_image(pil: Image.Image) -> bool:
    """Basic check for brain MRI - relaxed."""
    try:
        # Must be grayscale-like
        if not _is_grayscale_like(pil):
            return False
        return True  # Accept if grayscale-like
    except Exception:
        return False

def predict_image(img):
    try:
        if model is None:
            return "Model not loaded", 0.0, "No explanation available."
        if img is None:
            return "No image uploaded", 0.0, "Please upload an image."
        
        # Validate if it's a brain image
        if not _is_brain_image(img):
            return "Error: Please upload a correct brain MRI image.", 0.0, "The uploaded image does not appear to be a valid brain MRI scan. Please upload a proper medical image."
        
        img = img.resize((224, 224))
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array /= 255.0

        predictions = model.predict(img_array)
        predicted_class = np.argmax(predictions, axis=1)[0]
        confidence = np.max(predictions)
        label = labels.get(str(predicted_class), f"Class {predicted_class}")

        print(f"Debug: predictions {predictions}, class {predicted_class}, conf {confidence}, label {label}")

        # Explanation
        if label.lower() == 'notumor':
            explanation = f"No tumor detected with {confidence:.2f} confidence. The image appears normal."
        else:
            explanation = f"Detected {label} with {confidence:.2f} confidence. This indicates a potential brain tumor. Consult a medical professional for diagnosis."

        return label, confidence, explanation
    except Exception as e:
        print(f"Error in predict_image: {e}")
        return "Prediction error", 0.0, f"An error occurred: {str(e)}"

# Global for last prediction
last_pred = None
last_conf = None

def predict_and_update(img):
    global last_pred, last_conf
    label, conf, exp = predict_image(img)
    last_pred = label
    last_conf = conf
    return label, f"{conf:.2f}", exp

def chat_with_context(message):
    return chat_response(message, last_pred, last_conf)

with gr.Blocks(title="Brain Tumor Detection & Chat Assistant") as demo:
    gr.Markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: #4CAF50; animation: pulse 2s infinite;">🧠 Neuro Assist</h1>
        <div style="font-size: 18px; color: #666; margin: 10px 0;">
            Advanced Brain Tumor Detection & Analysis System
        </div>
        <div style="width: 100px; height: 100px; margin: 20px auto; border: 4px solid #f3f3f3; border-top: 4px solid #4CAF50; border-radius: 50%; animation: spin 2s linear infinite;"></div>
    </div>
    <style>
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """)
    
    with gr.Tab("Prediction"):
        image_input = gr.Image(label="Upload Brain MRI Image", type="pil")
        predict_btn = gr.Button("Predict")
        label_output = gr.Textbox(label="Prediction")
        confidence_output = gr.Textbox(label="Confidence")
        explanation_output = gr.Textbox(label="Explanation")
        
        predict_btn.click(
            fn=predict_and_update,
            inputs=image_input,
            outputs=[label_output, confidence_output, explanation_output]
        )
    
    with gr.Tab("Chat Assistant"):
        chat_input = gr.Textbox(label="Ask a question")
        chat_btn = gr.Button("Ask")
        chat_output = gr.Textbox(label="Response")
        
        chat_btn.click(
            fn=chat_with_context,
            inputs=chat_input,
            outputs=chat_output
        )

if __name__ == "__main__":
    demo.launch()