# 🧠 Neuro ASSIST - AI Brain Tumor Detection with 3D Animations

A stunning web application featuring beautiful 3D neural network animations with sliding colors, powered by AI for brain tumor detection and medical assistance.

## ✨ Features

- **🎨 3D Animation Landing Page**: Beautiful sliding color gradients with animated neural networks
- **🤖 AI Brain Tumor Detection**: Advanced deep learning models for accurate tumor classification
- **💬 Intelligent Chat Assistant**: LLM-powered medical consultation and explanations
- **📊 Explainable AI**: Class Activation Maps (CAM) showing model focus areas
- **🎯 High Accuracy**: Trained on thousands of brain MRI scans

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Trained model files in `models/` directory
- Dependencies listed in `requirements.txt`

### Installation
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Run the Application
```bash
# Option 1: Using the batch file (Windows)
start_server.bat

# Option 2: Direct Python execution
python fastapi_app.py
```



## 📁 Project Structure

```
├── frontend/
│   ├── index.html          # 3D animation landing page
│   └── neuro_assist.html   # Gradio interface
├── models/
│   ├── model.h5           # TensorFlow/Keras model
│   ├── labels.json        # Class labels mapping
│   └── training_results.json
├── brain tumor/           # Dataset directory
├── fastapi_app.py         # FastAPI backend server
├── app.py                # Gradio prototype
└── requirements.txt      # Python dependencies
```

## 🔧 Configuration

### Enable LLM Chat (Optional)
Set your OpenAI API key for intelligent medical conversations:
```bash
# Windows PowerShell
setx OPENAI_API_KEY "your_openai_api_key_here"
```

### Model Setup
- Place your trained model in `models/model.h5` or `models/model_selected.h5`
- Ensure `models/labels.json` exists with class mappings

## 🎨 Animation Features

The landing page showcases:
- **Sliding Color Backgrounds**: Dynamic gradient animations
- **3D Neural Networks**: Animated nodes and connections
- **Floating Color Orbs**: Interactive visual elements
- **Responsive Design**: Works on all devices

## 📡 API Endpoints

- `GET /` - Landing page with 3D animations
- `POST /predict` - Image prediction with CAM visualization
- `POST /chat` - AI-powered medical consultation
- `GET /frontend/*` - Static frontend files

## ⚠️ Important Notes

- This tool is for research and educational purposes only
- Always consult medical professionals for actual diagnosis
- Model predictions should be validated by qualified clinicians

## 🤝 Contributing

Feel free to enhance the animations, improve the AI models, or add new features!

Prerequisites
- Python 3.8+
- Place your trained PyTorch model at `models/model.pth`.
- (Optional) Provide `models/labels.json` with a mapping from class index to label, e.g. `{ "0": "No Tumor", "1": "Benign", "2": "Malignant" }`.

If your training was done in TensorFlow / Keras (this repository's notebook uses Keras):
- Use the export script to standardize model artifacts into the `models/` folder.

Save model from a notebook session (quick snippet):
```python
# inside your notebook after training completes
import os
os.makedirs('models', exist_ok=True)
# save SavedModel format
model.save('models/model_tf')
# save HDF5 copy
model.save('models/model.h5')
# save labels
import json
labels = ['glioma_tumor','meningioma_tumor','no_tumor','pituitary_tumor']
with open('models/labels.json','w') as f:
	json.dump({str(i): v for i, v in enumerate(labels)}, f, indent=2)
```

Or run the helper script (from repo root) to copy an existing `.h5` or SavedModel into `models/` and optionally convert to ONNX:
```
python scripts/export_keras_artifacts.py --input /path/to/your/model.h5 --labels-file labels.txt
```
Where `labels.txt` is one label per line.

TensorFlow/Keras native serving
- The `app.py` now supports serving TensorFlow/Keras models directly. If you place a Keras HDF5 file at `models/model.h5` or a SavedModel directory at `models/model_tf/`, the app will load that model and use `tf-keras-vis` to compute Grad-CAM visualizations.
- You do not need to convert Keras models to PyTorch — simply save into `models/` and run the app.

Install and run (PowerShell):
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open the URL that Gradio prints (usually `http://127.0.0.1:7860`).

Customization notes
- If you saved only `state_dict`, modify `load_model()` in `app.py` to construct your model class and call `load_state_dict()`.
 - If you saved only `state_dict`, the app will now attempt to auto-detect and load it. It will try to reconstruct a ResNet50 backbone and adapt the final layer to the number of classes inferred from the state_dict. If your model uses a different architecture, update `load_model()` in `app.py` to construct your model class and call `load_state_dict()`.
- If your model uses a different input size, update the preprocessing `transform`.
- To replace the rule-based chat assistant with an LLM, add an LLM client and forward context (last prediction and Grad-CAM summary) to the model.
 - To enable OpenAI-based chat responses, set the `OPENAI_API_KEY` environment variable before running the app.
	Example (PowerShell):
```
$env:OPENAI_API_KEY = "sk-..."
python app.py
```
	Optionally set `OPENAI_MODEL` (default `gpt-3.5-turbo`) to choose another chat model.

Security & privacy
- MRI images are sensitive. For production, ensure HTTPS, access controls, and secure storage.
