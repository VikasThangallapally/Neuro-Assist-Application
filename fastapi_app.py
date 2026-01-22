"""FastAPI backend to serve model inference and a minimal frontend.

Endpoints:
 - GET / -> serves a minimal static HTML frontend
 - POST /predict -> accepts form file `image`, returns JSON {label, confidence, cam_image (base64)}
 - POST /chat -> accepts JSON {message}, returns chat reply (LLM or rule-based)

Run:
  uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
"""
import os
import io
import base64
import json
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import FileResponse
from fastapi import Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
import numpy as np
import uuid
from typing import Dict, Any
import asyncio
import pathlib
import time
import logging
import re
import shutil
import secrets

try:
    import cv2
except Exception:
    cv2 = None

try:
    import openai
except Exception:
    openai = None

# Import medical knowledge base
try:
    from medical_knowledge import get_tumor_analysis, get_medication_side_effects, get_lifestyle_recommendations
except Exception:
    def get_tumor_analysis(label, conf):
        return {"name": label, "confidence": f"{conf*100:.1f}%", "error": "Medical knowledge base not available"}
    def get_medication_side_effects(label):
        return {}
    def get_lifestyle_recommendations(label):
        return []

# Also try to import enhanced brain tumor knowledge
try:
    from brain_tumor_knowledge import get_tumor_info, answer_question
    HAS_BRAIN_TUMOR_KB = True
except Exception:
    HAS_BRAIN_TUMOR_KB = False
    def answer_question(q):
        return "I can help with brain tumor questions. Please ask a specific question."

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
if openai is not None and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

app = FastAPI()

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'frontend')
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Try to import tensorflow and torch as available
USE_TF = False
USE_TORCH = False
tf_model = None
torch_model = None
alt_tf_model = None

# Allow quick imports for diagnostics/tests by setting SKIP_MODEL_LOAD=1 in the environment.
SKIP_MODEL_LOAD = os.environ.get('SKIP_MODEL_LOAD', '0') == '1'
alt_tf_model = None

if not SKIP_MODEL_LOAD:
    try:
        import tensorflow as tf
        USE_TF = True
    except Exception:
        USE_TF = False
else:
    # Skip importing TensorFlow to speed up lightweight diagnostics
    USE_TF = False

try:
    import torch
    USE_TORCH = True
except Exception:
    USE_TORCH = False

# load models from models/
LABELS = {}
if os.path.exists('models/labels.json'):
    with open('models/labels.json', 'r', encoding='utf-8') as f:
        LABELS = json.load(f)

# Optional models evaluation summary (contains best_model, best_accuracy, etc.)
MODELS_EVAL = {}
if os.path.exists('models/models_evaluation.json'):
    try:
        with open('models/models_evaluation.json', 'r', encoding='utf-8') as ef:
            MODELS_EVAL = json.load(ef)
    except Exception:
        MODELS_EVAL = {}

model_path = None
# Prefer explicitly selected model, otherwise fall back to model.h5
if os.path.exists('models/model_selected.h5'):
    model_path = 'models/model_selected.h5'
elif os.path.exists('models/model.h5'):
    model_path = 'models/model.h5'

if USE_TF and model_path:
    try:
        tf_model = tf.keras.models.load_model(model_path)
        print(f'Loaded TF model from {model_path}')
    except Exception:
        tf_model = None
        print(f'Failed to load TF model from {model_path}')

    # Also look for an optional LIME/alternate model saved as models/lime*.h5
    try:
        for fname in os.listdir('models') if os.path.exists('models') else []:
            if fname.lower().endswith('.h5') and 'lime' in fname.lower():
                alt_path = os.path.join('models', fname)
                try:
                    alt_tf_model = tf.keras.models.load_model(alt_path)
                    print(f'Loaded alternate LIME model from {alt_path}')
                    break
                except Exception:
                    alt_tf_model = None
    except Exception:
        alt_tf_model = None

if USE_TORCH and os.path.exists('models/model.pth'):
    try:
        torch_model = torch.load('models/model.pth', map_location='cpu')
        torch_model.eval()
    except Exception:
        torch_model = None

# In-memory per-session store (fallback): session_id -> { last_prediction, last_confidence, ... }
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

# Redis async client (optional, used in production via docker-compose)
redis_client = None
try:
    import redis.asyncio as redis_asyncio
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    # create a redis client instance; we'll connect lazily
    redis_client = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
except Exception:
    redis_client = None

# In-memory rate limit fallback store: (session_id, period) -> count
LLM_RATE_STORE = {}

# Logging
logger = logging.getLogger('fastapi_app')
logging.basicConfig(level=logging.INFO)

# Attempt deferred model loading with custom objects (now that logger exists)
if USE_TF and tf_model is None and os.path.exists('models/model.h5'):
    try:
        from models.feature_rf_wrapper import FeatureRFModel
        tf_model = tf.keras.models.load_model('models/model.h5', custom_objects={'FeatureRFModel': FeatureRFModel})
        logger.info('Loaded model.h5 using custom FeatureRFModel wrapper')
    except Exception as e:
        logger.warning('Could not load model.h5 with FeatureRFModel wrapper: %s', e)
        # Model remains None; /predict will return error

# LLM security/config
LLM_ENABLED = os.environ.get('LLM_ENABLED', '1') in ['1', 'true', 'True']
LLM_RATE_LIMIT_PER_MIN = int(os.environ.get('LLM_RATE_LIMIT_PER_MIN', '6'))

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b\+?\d[\d\-\s]{7,}\b")


def _contains_pii(text: str) -> bool:
    if not text:
        return False
    if _EMAIL_RE.search(text):
        return True
    if _SSN_RE.search(text):
        return True
    if _PHONE_RE.search(text):
        return True
    # long digit sequences (e.g., IDs)
    if re.search(r"\b\d{9,}\b", text):
        return True
    return False


async def _llm_check_and_increment(session_id: str) -> bool:
    """Return True if under rate limit, increment counter. Use Redis if available, otherwise in-memory fallback."""
    if session_id is None:
        session_id = 'anon'
    period = int(time.time() // 60)
    if redis_client is not None:
        try:
            key = f"llm_rl:{session_id}:{period}"
            n = await redis_client.incr(key)
            if n == 1:
                await redis_client.expire(key, 70)
            logger.debug('LLM rate key %s -> %s', key, n)
            return n <= LLM_RATE_LIMIT_PER_MIN
        except Exception:
            # fallback to in-memory if Redis errors
            pass

    # in-memory fallback
    key = (session_id, period)
    cnt = LLM_RATE_STORE.get(key, 0) + 1
    LLM_RATE_STORE[key] = cnt
    # simple cleanup: remove old keys occasionally
    if len(LLM_RATE_STORE) > 10000:
        nowp = int(time.time() // 60)
        for k in list(LLM_RATE_STORE.keys()):
            if k[1] < nowp - 2:
                del LLM_RATE_STORE[k]
    return cnt <= LLM_RATE_LIMIT_PER_MIN


async def _redis_get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve session dict from Redis or return {} if not present."""
    if redis_client is None:
        return {}
    try:
        key = f"session:{session_id}"
        raw = await redis_client.get(key)
        if not raw:
            return {}
        return json.loads(raw)
    except Exception:
        return {}


async def _redis_set_session(session_id: str, data: Dict[str, Any], ttl: int = 60 * 60 * 24):
    """Store session dict into Redis with TTL (seconds)."""
    if redis_client is None:
        return
    try:
        key = f"session:{session_id}"
        await redis_client.set(key, json.dumps(data), ex=ttl)
    except Exception:
        return


# Safe, non-diagnostic explanations for labels. Keep short, non-medical and include disclaimer.
EXPLANATIONS = {}
# Populate default safe explanations from LABELS when available
for k, v in LABELS.items():
    if k not in EXPLANATIONS:
        EXPLANATIONS[k] = (
            f"The model identified '{v}' as the most likely label. This is an automated, non-diagnostic summary — "
            "consult a radiologist or treating physician for interpretation and next steps."
        )

# Load global canned QA (exact question -> answer) if present
GLOBAL_QA = {}
try:
    gqf = pathlib.Path('outputs') / 'batch' / 'global_qa.json'
    if gqf.exists():
        with open(gqf, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            # normalize questions
            def _norm(s: str) -> str:
                import re
                s = s.lower().strip()
                s = re.sub(r"[^a-z0-9\s]", '', s)
                s = re.sub(r"\s+", ' ', s)
                return s
            for item in raw:
                q = item.get('question')
                a = item.get('answer')
                if q and a:
                    GLOBAL_QA[_norm(q)] = a
        # also prepare a list for fuzzy matching
        GLOBAL_QA_LIST = list(GLOBAL_QA.keys())
    else:
        GLOBAL_QA_LIST = []
except Exception:
    GLOBAL_QA = {}
    GLOBAL_QA_LIST = []


def _find_canned_answer(text: str, threshold: int = 85):
    """Return canned answer for text using exact or fuzzy match."""
    try:
        import re
        nm = re.sub(r"[^a-z0-9\s]", '', (text or '').lower()).strip()
        nm = re.sub(r"\s+", ' ', nm)
    except Exception:
        nm = (text or '').lower().strip()

    # exact
    if nm in GLOBAL_QA:
        return GLOBAL_QA[nm]

    # fuzzy: try RapidFuzz if available
    try:
        from rapidfuzz import process, fuzz
        if GLOBAL_QA_LIST:
            match = process.extractOne(nm, GLOBAL_QA_LIST, scorer=fuzz.ratio)
            if match and match[1] >= threshold:
                return GLOBAL_QA[match[0]]
    except Exception:
        # fallback to difflib
        try:
            import difflib
            if GLOBAL_QA_LIST:
                cand = difflib.get_close_matches(nm, GLOBAL_QA_LIST, n=1, cutoff=threshold/100.0)
                if cand:
                    return GLOBAL_QA[cand[0]]
        except Exception:
            pass

    return None


def _rule_explanation(label: str, confidence: float) -> str:
    """Return a safe, non-diagnostic explanation for the predicted label and confidence."""
    lab_key = label
    # if label names rather than numeric keys are used in LABELS, try reverse lookup
    if lab_key not in EXPLANATIONS:
        # try to find numeric key from LABELS
        for k, v in LABELS.items():
            if v == label:
                lab_key = k
                break
    expl = EXPLANATIONS.get(lab_key)
    if not expl:
        expl = f"Model predicted {label} with confidence {confidence:.2f}. This is only an automated assessment; consult a clinician for medical interpretation."
    return expl

def _split_explanation_to_messages(label: str, confidence: float, medical_analysis: dict) -> list:
    """Split the medical explanation into separate chat messages (one by one)."""
    messages = []
    conf_percent = confidence * 100
    
    # Message 1: Tumor Detection Confidence
    msg1 = f"📊 **TUMOR DETECTION CONFIDENCE (Model Accuracy)**\n\n"
    msg1 += f"Confidence Score: {conf_percent:.1f}%\n\n"
    msg1 += f"• What this means: The AI model has analyzed your brain MRI and is {conf_percent:.1f}% confident in its assessment.\n"
    msg1 += f"• Higher percentage = Higher certainty in the prediction\n"
    msg1 += f"• ⚠️ Important: This is NOT a medical diagnosis - professional evaluation is always needed."
    messages.append({'type': 'analysis', 'text': msg1})
    
    # Message 2: Disease Information
    msg2 = f"🔍 **DISEASE INFORMATION**\n\n"
    detected_condition = medical_analysis.get('name', label) if medical_analysis else label
    msg2 += f"Detected Condition: {detected_condition}\n\n"
    
    if (detected_condition.lower() == 'no tumor') or ('normal' in detected_condition.lower()):
        msg2 += f"Description: The brain MRI scan shows no detectable tumor.\n"
        msg2 += f"Classification: Normal brain tissue detected\n\n"
        msg2 += f"✅ Key Information:\n"
        msg2 += f"• Status: Normal brain tissue detected\n"
        msg2 += f"• Note: This is a positive result indicating normal brain structure"
    else:
        msg2 += f"Description: {medical_analysis.get('description', 'Brain abnormality detected')}\n\n"
        msg2 += f"📋 Classification Details:\n"
        msg2 += f"• Tumor Type: {detected_condition}\n"
        msg2 += f"• Confidence: {conf_percent:.1f}%"
    messages.append({'type': 'disease', 'text': msg2})
    
    # Message 3: Symptoms & Warning Signs
    msg3 = f"⚠️ **COMMON SYMPTOMS & WARNING SIGNS**\n\n"
    if (detected_condition.lower() == 'no tumor') or ('normal' in detected_condition.lower()):
        msg3 += f"STATUS: No tumor-related symptoms expected\n"
        msg3 += f"Normal brain tissue indicates no pathology detected\n\n"
        msg3 += f"Important Notes:\n"
        msg3 += f"• Not all patients experience all symptoms\n"
        msg3 += f"• Symptoms depend on tumor location, size, and type\n"
        msg3 += f"• Presence of symptoms doesn't confirm diagnosis\n"
        msg3 += f"• Absence of symptoms doesn't mean it's not serious"
    else:
        msg3 += f"Potential Symptoms (if tumor confirmed):\n"
        msg3 += f"• Headaches\n"
        msg3 += f"• Vision problems\n"
        msg3 += f"• Balance and coordination issues\n"
        msg3 += f"• Nausea or vomiting\n\n"
        msg3 += f"Important Notes:\n"
        msg3 += f"• Not all patients experience all symptoms\n"
        msg3 += f"• Symptoms depend on tumor location, size, and type"
    messages.append({'type': 'symptoms', 'text': msg3})
    
    # Message 4: Side Effects & Treatment
    msg4 = f"💊 **POTENTIAL SIDE EFFECTS & TREATMENT CONSIDERATIONS**\n\n"
    msg4 += f"Treatment Selection depends on:\n"
    msg4 += f"• Tumor size, location, and grade\n"
    msg4 += f"• Patient age and overall health\n"
    msg4 += f"• Patient preferences\n\n"
    msg4 += f"Available Treatment Options:\n"
    msg4 += f"• Surgery\n"
    msg4 += f"• Radiation therapy\n"
    msg4 += f"• Chemotherapy\n"
    msg4 += f"• Clinical trials\n\n"
    msg4 += f"Note: Multiple treatment options may be available. Your doctor will recommend the best approach for your specific case."
    messages.append({'type': 'treatment', 'text': msg4})
    
    # Message 5: Doctor Recommendations
    msg5 = f"👨‍⚕️ **URGENT: DOCTOR VISIT RECOMMENDATIONS**\n\n"
    msg5 += f"Next Steps:\n"
    msg5 += f"1. Consult with a Neurologist or Neurosurgeon\n"
    msg5 += f"2. Have your MRI reviewed by a Radiologist\n"
    msg5 += f"3. Discuss additional imaging if needed\n"
    msg5 += f"4. Create a personalized treatment plan\n\n"
    msg5 += f"⚠️ Disclaimer:\n"
    msg5 += f"This AI analysis is a supplementary tool ONLY. Always consult qualified medical professionals for diagnosis and treatment. This report should not replace professional medical advice."
    messages.append({'type': 'recommendation', 'text': msg5})
    
    return messages


def _build_explanation_prompt(label_idx: str, label_name: str, confidence: float, top_k: list, probs_map: dict):
    ctx = [f"Top predictions:" ]
    for item in top_k:
        ctx.append(f"- {item.get('label')}: {item.get('probability'):.3f}")
    ctx_text = "\n".join(ctx)
    prompt = (
        "You are an assistant that explains the output of an image classification model for educational purposes. "
        "You MUST NOT provide medical diagnoses or definitive clinical advice. Include a clear disclaimer recommending consultation with a clinician. "
        "Keep the language non-technical and concise (2-3 sentences).\n\n"
        f"Model label: {label_name} (id: {label_idx}), confidence: {confidence:.3f}.\n"
        f"{ctx_text}\n\n"
        "Write a short, non-diagnostic explanation of what this model output may indicate and safe next steps (e.g., consult a radiologist, consider follow-up imaging)."
    )
    return prompt


def llm_explanation(label_idx: str, label_name: str, confidence: float, top_k: list, probs_map: dict) -> str:
    """Generate a safe, non-diagnostic explanation using OpenAI. Falls back to rule-based explanation on error."""
    if openai is None or OPENAI_API_KEY is None:
        return _rule_explanation(label_name, confidence)

    system_prompt = (
        "You are a careful assistant that summarizes and explains model outputs. NEVER give medical diagnoses. Always include a disclaimer and recommend consulting a licensed medical professional."
    )
    user_prompt = _build_explanation_prompt(label_idx, label_name, confidence, top_k, probs_map)
    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            max_tokens=200,
            temperature=0.2,
        )
        return resp['choices'][0]['message']['content'].strip()
    except Exception:
        return _rule_explanation(label_name, confidence)


async def _get_or_create_session_id(request: Request) -> str:
    """Return existing session_id from cookie or create a new one and persist an empty session.

    Uses Redis if available, otherwise falls back to in-memory store.
    """
    sid = request.cookies.get('session_id')
    if sid:
        return sid
    sid = str(uuid.uuid4())
    # initialize an empty session in Redis or fallback store
    initial = {'history': []}
    if redis_client is not None:
        await _redis_set_session(sid, initial)
    else:
        SESSION_STORE.setdefault(sid, initial)
    return sid


def _build_prediction_qa(label: str, confidence: float, top_k: list) -> list:
    """Return a short list of suggested user questions and LLM-like answers for the given prediction.

    Uses the configured LLM when available; falls back to rule-based answers.
    """
    questions = [
        "What does this result mean?",
        "How confident is the model in this result?",
        "What are safe next steps?",
        "What symptoms or signs are associated with this tumor type?"
    ]
    qa = []
    for q in questions:
        try:
            if openai is not None and OPENAI_API_KEY is not None:
                try:
                    # use llm_chat to keep answers consistent with assistant persona
                    ans = llm_chat(q + f" Context: prediction {label} (confidence {confidence:.2f}).", last_pred=label, last_conf=confidence)
                except Exception:
                    ans = rule_based_chat(q, last_pred=label, last_conf=confidence)
            else:
                ans = rule_based_chat(q, last_pred=label, last_conf=confidence)
        except Exception:
            ans = "I can help explain model outputs. Please consult a clinician for medical advice."
        qa.append({'question': q, 'answer': ans})
    return qa


def pil_to_base64(img: Image.Image):
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _is_grayscale_like(pil: Image.Image) -> bool:
    """Check if the image is mostly grayscale (low color variance) - validation for MRI."""
    try:
        arr = np.array(pil.resize((256, 256)))
        if arr.ndim == 2:
            # Single channel - definitely grayscale (valid MRI)
            return True
        if arr.shape[2] < 3:
            return False
        
        r, g, b = arr[:, :, 0].astype(float), arr[:, :, 1].astype(float), arr[:, :, 2].astype(float)
        diff_rg = np.abs(r - g).mean()
        diff_rb = np.abs(r - b).mean()
        diff_gb = np.abs(g - b).mean()
        
        # Medical MRI images must be mostly grayscale
        # Threshold: 30 allows for slight color variations due to image conversion
        is_grayscale = diff_rg < 30 and diff_rb < 30 and diff_gb < 30
        
        return is_grayscale
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
        # Medical images often have specific intensity ranges
        hist, bins = np.histogram(arr.ravel(), bins=256, range=(0, 255))
        hist_norm = hist / hist.sum()

        # Check for characteristic peaks in histogram
        # Medical images often have peaks in certain intensity ranges
        low_intensities = hist_norm[0:64].sum()  # Very dark areas
        mid_intensities = hist_norm[64:192].sum()  # Mid-range (tissue)
        high_intensities = hist_norm[192:256].sum()  # Bright areas

        # Check for noise patterns
        # Medical images have characteristic noise vs natural images
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

        # Look for circular/elliptical structures (brain cross-sections)
        # Use Hough circle transform approximation
        edges = cv2.Canny(arr, 50, 150)

        # Count circular shapes using contour detection
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        circular_contours = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)

            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                # Check for roughly circular shapes
                if 0.3 < circularity < 0.9 and area > 100:
                    circular_contours += 1

        # Brain images typically have several circular/elliptical structures
        return circular_contours >= 2

    except Exception:
        return False


def _is_brain_image(pil: Image.Image) -> bool:
    """Check if the uploaded image is a valid brain MRI scan.
    
    Simple validation:
    1. Must be grayscale-like (MRI requirement)
    2. Must have reasonable size
    3. Must have reasonable contrast
    
    Returns True for valid brain MRI images, False otherwise.
    """
    try:
        # Step 1: Must be grayscale-like
        if not _is_grayscale_like(pil):
            logging.debug("Image rejected: Not grayscale-like")
            return False
        
        # Step 2: Check image dimensions are reasonable
        width, height = pil.size
        
        # Minimum reasonable size
        if width < 64 or height < 64:
            logging.debug(f"Image rejected: Too small ({width}x{height})")
            return False
        
        # Maximum reasonable size (shouldn't be huge)
        if width > 2000 or height > 2000:
            logging.debug(f"Image rejected: Too large ({width}x{height})")
            return False
        
        # Step 3: Check contrast - medical images should have reasonable contrast
        gray = pil.convert('L')
        arr = np.array(gray).astype('float32')
        std_val = np.std(arr)
        
        # Very low contrast images are likely not medical scans
        if std_val < 5:
            logging.debug(f"Image rejected: Very low contrast (std={std_val:.1f})")
            return False
        
        logging.info("Image validated as brain MRI")
        return True
        
    except Exception as e:
        logging.error(f"Error validating brain image: {e}")
        return False
        
    except Exception as e:
        logging.error(f"Error in brain image validation: {e}")
        return False


def _has_focus_area(pil: Image.Image) -> bool:
    """Check whether the central/focus area of the image contains MRI brain structures.

    Heuristic: examine the center crop (middle 50%); require a minimum fraction of non-background
    pixels and a minimum contrast. Returns False when the central region looks empty/flat.
    """
    try:
        gray = pil.convert('L').resize((256, 256))
        arr = np.array(gray).astype('float32')
        h, w = arr.shape
        cy1, cy2 = int(h * 0.25), int(h * 0.75)
        cx1, cx2 = int(w * 0.25), int(w * 0.75)
        central = arr[cy1:cy2, cx1:cx2]
        # fraction of pixels that are not almost-black (background) and not pure white
        non_bg = float(((central > 15) & (central < 240)).sum()) / central.size
        central_std = float(central.std())
        # stricter thresholds but allow more
        if non_bg < 0.05 or central_std < 5.0:
            return False
        return True
    except Exception:
        return False


def rule_based_chat(message, last_pred=None, last_conf=None):
    """Enhanced chat that understands questions better and provides ChatGPT-like responses."""
    msg = message or ''
    msg_lower = msg.lower().strip()
    
    # Check for invalid image first
    if last_pred and 'invalid' in last_pred.lower():
        return 'The uploaded image appears to be invalid or not a brain MRI scan. Please upload a valid grayscale brain MRI image for analysis.'
    
    # No prediction available yet
    if last_pred is None:
        # Help user understand they need to upload an image first
        if any(word in msg_lower for word in ['what', 'how', 'why', 'can', 'will', 'is', 'does']):
            return f'To answer your question about brain MRI analysis, I first need you to upload a brain MRI image. Once you upload an image, I can analyze it and answer questions like: "{message}". Please upload a valid brain MRI image first.'
        return 'No prediction available yet. Please upload a brain MRI image first, then I can answer your questions about it.'
    
    # Try enhanced brain tumor knowledge base for comprehensive answers
    if HAS_BRAIN_TUMOR_KB:
        try:
            answer = answer_question(message)
            if answer and "specific question" not in answer.lower() and len(answer) > 20:
                return answer
        except Exception:
            pass
    
    conf_percent = last_conf * 100 if last_conf is not None else 0
    
    # ===== GREETING & FRIENDLY RESPONSES =====
    if any(word in msg_lower for word in ['hi ', 'hello', 'hey', 'greetings', 'how are']):
        return f'Hello! I analyzed your brain MRI and detected: **{last_pred}** with **{conf_percent:.1f}% confidence**. Feel free to ask me any questions about this result, such as what this means, treatment options, symptoms, or anything else you\'d like to know!'
    
    if any(word in msg_lower for word in ['thank', 'thanks', 'appreciate']):
        return 'You\'re welcome! I\'m here to help you understand your brain MRI results. Is there anything else you\'d like to know?'
    
    # ===== QUESTIONS ABOUT WHAT WAS DETECTED =====
    if any(phrase in msg_lower for phrase in ['what did you find', 'what did you detect', 'what\'s the result', 'what tumor', 'what is the', 'tell me the result']):
        return f'I detected **{last_pred}** in your brain MRI scan with **{conf_percent:.1f}% confidence**. This means the model assessed the image and identified this tumor type as the most likely diagnosis based on the scan patterns.'
    
    if any(phrase in msg_lower for phrase in ['what does it mean', 'what does this mean', 'what is this', 'explain the result']):
        if 'glioma' in last_pred.lower():
            return f'**{last_pred}** is a type of brain tumor that originates from glial cells (supporting cells in the brain). Gliomas can vary in grade and severity, ranging from low-grade (slow-growing) to high-grade (aggressive). The exact treatment depends on the grade, size, and location.'
        elif 'meningioma' in last_pred.lower():
            return f'**{last_pred}** is a tumor of the meninges - the protective membranes surrounding the brain and spinal cord. Most meningiomas are benign (non-cancerous) and slow-growing. However, treatment may still be needed depending on size and location.'
        elif 'pituitary' in last_pred.lower():
            return f'**{last_pred}** originates from the pituitary gland, a small but important gland at the base of the brain. These tumors can affect hormone production and may cause various symptoms. Treatment options include medication, surgery, or radiation depending on the tumor size and type.'
        elif 'no_tumor' in last_pred.lower() or 'no tumor' in last_pred.lower():
            return f'The scan shows **{last_pred}** - meaning no detectable tumor was found. This is a positive result indicating normal brain tissue without apparent pathology based on the model\'s analysis.'
        else:
            return f'The predicted diagnosis is **{last_pred}**. This is the model\'s assessment of what it identified in the MRI scan. For detailed medical interpretation, please consult with a neurologist or radiologist.'
    
    # ===== CONFIDENCE/ACCURACY QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['how confident', 'how sure', 'how accurate', 'confidence level', 'how reliable', 'is it accurate']):
        reliability = "very high" if conf_percent >= 85 else "high" if conf_percent >= 70 else "moderate" if conf_percent >= 50 else "low"
        return f'The model has **{conf_percent:.1f}% confidence** in this prediction, which represents {reliability} confidence. This means there\'s a {conf_percent:.1f}% probability the model is correct. However, this is still a machine learning prediction and should be confirmed by a professional radiologist or neurologist for final diagnosis.'
    
    # ===== SYMPTOMS QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['symptoms', 'signs', 'what are symptoms', 'what causes symptoms', 'will i have', 'can cause', 'common symptoms']):
        if 'glioma' in last_pred.lower():
            return f'**{last_pred}** commonly presents with: headaches, seizures, vision changes, difficulty with balance, cognitive changes, or speech difficulties. Symptoms depend on tumor location and size. However, not all patients experience symptoms. **Important**: Always consult a neurologist about your specific symptoms.'
        elif 'meningioma' in last_pred.lower():
            return f'**{last_pred}** may cause: headaches, vision problems, hearing issues, balance difficulties, or cognitive changes. Many meningiomas grow slowly and may not cause symptoms initially. **Please consult a neurologist to discuss whether your symptoms match this prediction.**'
        elif 'pituitary' in last_pred.lower():
            return f'**{last_pred}** can cause: hormonal imbalances, headaches, vision loss (especially peripheral vision), fatigue, or sexual dysfunction. Symptoms depend on which hormones are affected. **Consult an endocrinologist or neurologist for symptom evaluation and management.**'
        else:
            return f'Symptoms related to {last_pred} vary by individual. Please consult a healthcare professional to discuss your specific symptoms and how they relate to this diagnosis.'
    
    # ===== TREATMENT QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['treatment', 'cure', 'how to treat', 'what is the treatment', 'surgery', 'therapy', 'medication', 'how to fix', 'how can it be treated']):
        if 'glioma' in last_pred.lower():
            return f'Treatment for **{last_pred}** typically involves: 1) **Surgery** - to remove or biopsy the tumor, 2) **Radiation therapy** - to target cancer cells, 3) **Chemotherapy** - systemic drug treatment, or combinations of these. The best approach depends on grade, size, and location. **You must discuss with an oncologist and neurosurgeon for a personalized treatment plan.**'
        elif 'meningioma' in last_pred.lower():
            return f'Treatment for **{last_pred}** may include: 1) **Observation** - if it\'s small and not causing symptoms, 2) **Surgery** - if it\'s growing or symptomatic, 3) **Radiation therapy** - in certain cases. Many meningiomas can be managed conservatively. **Consult a neurosurgeon to determine the best approach for your case.**'
        elif 'pituitary' in last_pred.lower():
            return f'Treatment for **{last_pred}** options include: 1) **Medication** - to control hormone levels, 2) **Surgery** - if the tumor is large or causing vision problems, 3) **Radiation therapy** - in some cases. **An endocrinologist and neurosurgeon can determine the best treatment strategy for you.**'
        else:
            return f'Treatment options for {last_pred} vary based on many factors. **Please consult with a qualified neurologist or oncologist to discuss the best treatment approach for your specific case.**'
    
    # ===== PROGNOSIS/OUTCOME QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['prognosis', 'survive', 'survival rate', 'outcome', 'how serious', 'will i be ok', 'recovery', 'long term', 'life expectancy']):
        return f'Prognosis for **{last_pred}** depends on multiple factors including: tumor grade/stage, size, location, how early it was detected, and individual patient factors. **Survival rates and recovery prospects vary widely.** Early detection and proper treatment generally improve outcomes. **Consult an oncologist for personalized prognosis information based on your specific case.**'
    
    # ===== CAUSES/RISK FACTORS QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['cause', 'why did', 'how did i get', 'risk factors', 'what causes', 'is it hereditary', 'can it be prevented']):
        return f'The exact causes of **{last_pred}** are not fully understood. Possible risk factors may include: genetics, radiation exposure, certain genetic syndromes, hormonal factors, or other medical conditions. Most brain tumors are not preventable. **A neurologist can discuss your specific risk factors and family history.**'
    
    # ===== NEXT STEPS QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['next', 'what now', 'what should i do', 'what happens next', 'follow up', 'next steps', 'what to do']):
        return f'Recommended next steps after this prediction:\n1) **Schedule appointment** with a neurologist or neurosurgeon\n2) **Get professional evaluation** - share this MRI and analysis with your doctor\n3) **Discuss treatment** - consult about treatment options if needed\n4) **Get second opinion** - consider getting another medical professional\'s perspective\n5) **Follow-up imaging** - your doctor may recommend follow-up scans\n**This AI prediction is not a medical diagnosis - professional evaluation is essential.**'
    
    # ===== HEATMAP/EXPLANATION QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['heatmap', 'explain how', 'why this result', 'how did it decide', 'grad-cam', 'attention', 'focus', 'highlight']):
        return f'The **heatmap (Grad-CAM visualization)** shows which brain regions most influenced the model\'s prediction. **Bright/hot areas** = regions that strongly contributed to detecting {last_pred}. **Darker areas** = less influential regions. This helps you see where the model focused its analysis, though it\'s still an AI interpretation and needs professional confirmation.'
    
    # ===== COMPARISON QUESTIONS =====
    if any(phrase in msg_lower for phrase in ['difference between', 'vs', 'versus', 'compare', 'what\'s the difference']):
        return f'To compare {last_pred} with other tumor types, I\'d be happy to help! Could you specify which tumor type you\'d like to compare it with? I can explain differences between glioma, meningioma, pituitary tumors, etc.'
    
    # ===== GENERAL Q&A FALLBACK =====
    # If we don't match specific patterns, try to be helpful anyway
    if any(word in msg_lower for word in ['what', 'how', 'why', 'can', 'will', 'should', 'is']):
        return f'Your current prediction is **{last_pred}** (confidence: {conf_percent:.1f}%). Regarding your question about this, I can help explain:\n- What {last_pred} means\n- Symptoms and signs\n- Treatment options\n- Prognosis and recovery\n- Next steps to take\n**Please ask me specifically about any of these topics, and I\'ll provide detailed information.**'
    
    # Generic helpful response
    return f'You have **{last_pred}** detected in your scan with **{conf_percent:.1f}% confidence**. Feel free to ask me anything about this result - I can explain what it means, discuss treatment options, symptoms, prognosis, or anything else you\'d like to know. What would you like to learn about?'


def llm_chat(message: str, last_pred: str = None, last_conf: float = None) -> str:
    """Call OpenAI ChatCompletion to answer the user's message, using last prediction as context."""
    if openai is None or OPENAI_API_KEY is None:
        raise RuntimeError("OpenAI not configured")

    # Strong system prompt with tumor-specific context
    system_prompt = (
        "You are a knowledgeable medical assistant helping users understand their brain MRI analysis. "
        "You have access to a model prediction about a brain tumor. Provide accurate, helpful information about: "
        "- The predicted tumor type and what it means "
        "- Symptoms commonly associated with the prediction "
        "- General treatment approaches "
        "- Questions about the confidence level and what it means "
        "- Explanations about the medical terms "
        "- Next steps to take after getting a prediction "
        "\n"
        "IMPORTANT SAFETY RULES: "
        "1. Do NOT provide medical diagnoses or definitive clinical advice "
        "2. Always recommend consulting with a qualified neurologist or radiologist for final decisions "
        "3. If asked for medical advice beyond the prediction, redirect to healthcare professionals "
        "4. Do NOT interpret this as a replacement for professional medical evaluation "
        "5. Be compassionate and non-alarming in your tone "
        "6. Respond in the same language as the user's question "
        "7. Always emphasize that this is model output, not professional diagnosis "
    )

    # Build rich context about the prediction
    if last_pred and last_conf is not None:
        conf_percent = last_conf * 100
        context = (
            f"CURRENT PREDICTION CONTEXT:\n"
            f"- Model Prediction: {last_pred}\n"
            f"- Confidence Score: {conf_percent:.1f}%\n"
            f"- Confidence Interpretation: "
        )
        
        if conf_percent >= 80:
            context += "High confidence prediction\n"
        elif conf_percent >= 50:
            context += "Moderate confidence prediction\n"
        else:
            context += "Lower confidence - professional evaluation recommended\n"
        
        context += (
            "\nThe user is asking questions about their brain MRI analysis. "
            "Provide helpful, accurate information related to their prediction. "
            "Always remind them that this is a model assessment and professional medical evaluation is essential."
        )
    else:
        context = "The user hasn't uploaded a brain MRI image yet or the image was invalid. Direct them to upload a valid scan first."

    user_content = context + "\n\nUser's question: " + message

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=500,
            temperature=0.3,  # Slightly higher for better explanation quality
        )
        reply = resp['choices'][0]['message']['content'].strip()
        
        # Ensure safety disclaimer is included
        if "consult" not in reply.lower() and "professional" not in reply.lower():
            reply += "\n\nPlease consult a qualified medical professional for definitive diagnosis and treatment recommendations."
        
        return reply
    except Exception as e:
        # Fallback to rule-based if LLM fails
        raise RuntimeError(f"OpenAI request failed: {e}")


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    intro_path = os.path.join(TEMPLATES_DIR, 'neuro_intro.html')
    if os.path.exists(intro_path):
        with open(intro_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(f.read())
    index_path = os.path.join(TEMPLATES_DIR, 'index.html')
    if os.path.exists(index_path):
        return templates.TemplateResponse('index.html', {'request': request})
    return HTMLResponse('<h3>FastAPI backend is running. No frontend found.</h3>')




















@app.post('/predict')
async def predict(request: Request, image: UploadFile = File(...)):
    try:
        contents = await image.read()
        pil = Image.open(io.BytesIO(contents)).convert('RGB')

        # Prefer TF model if available
        global last_prediction, last_confidence
        if tf_model is not None:
            # Early MRI detection: reject non-MRI images before running the model
            try:
                if not _is_brain_image(pil):
                    sid = await _get_or_create_session_id(request)
                    resp_nb = {
                        'is_brain': False,
                        'message': 'Please upload a valid brain MRI image. Only grayscale MRI scans are supported.',
                        'models_evaluation': MODELS_EVAL,
                        'session_id': sid,
                    }
                    response = JSONResponse(resp_nb, status_code=400)
                    # Save invalid message in session
                    try:
                        if redis_client is not None:
                            s = await _redis_get_session(sid)
                            s['last_prediction'] = resp_nb['message']
                            s['last_confidence'] = 0.0
                            await _redis_set_session(sid, s)
                        else:
                            SESSION_STORE.setdefault(sid, {})['last_prediction'] = resp_nb['message']
                            SESSION_STORE.setdefault(sid, {})['last_confidence'] = 0.0
                    except Exception as e:
                        logging.warning(f"Failed to save invalid prediction to session: {e}")
                    response.set_cookie('session_id', sid, httponly=True)
                    return response
                # ensure the MRI is focused/centered on the brain region
                try:
                    # Disabled focus check to allow prediction on any brain image
                    # if not _has_focus_area(pil):
                    #     sid = await _get_or_create_session_id(request)
                    #     resp_nb = {
                    #         'is_brain': True,
                    #         'message': 'invalid image',
                    #         'models_evaluation': MODELS_EVAL,
                    #         'session_id': sid,
                    #     }
                    #     response = JSONResponse(resp_nb, status_code=400)
                    #     # Save invalid message in session
                    #     try:
                    #         if redis_client is not None:
                    #             s = await _redis_get_session(sid)
                    #             s['last_prediction'] = resp_nb['message']
                    #             s['last_confidence'] = 0.0
                    #             await _redis_set_session(sid, s)
                    #         else:
                    #             SESSION_STORE.setdefault(sid, {})['last_prediction'] = resp_nb['message']
                    #             SESSION_STORE.setdefault(sid, {})['last_confidence'] = 0.0
                    #     except Exception as e:
                    #         logging.warning(f"Failed to save invalid prediction to session: {e}")
                    #     response.set_cookie('session_id', sid, httponly=True)
                    #     return response
                    pass
                except Exception:
                    pass
            except Exception:
                # on error in validation, treat as invalid image
                sid = await _get_or_create_session_id(request)
                resp_nb = {
                    'is_brain': False,
                    'message': 'invalid image',
                    'models_evaluation': MODELS_EVAL,
                    'session_id': sid,
                }
                response = JSONResponse(resp_nb, status_code=400)
                # Save invalid message in session
                try:
                    if redis_client is not None:
                        s = await _redis_get_session(sid)
                        s['last_prediction'] = resp_nb['message']
                        s['last_confidence'] = 0.0
                        await _redis_set_session(sid, s)
                    else:
                        SESSION_STORE.setdefault(sid, {})['last_prediction'] = resp_nb['message']
                        SESSION_STORE.setdefault(sid, {})['last_confidence'] = 0.0
                except Exception as e:
                    logging.warning(f"Failed to save invalid prediction to session: {e}")
                response.set_cookie('session_id', sid, httponly=True)
                return response
            input_shape = None
            try:
                input_shape = (int(tf_model.inputs[0].shape[1]), int(tf_model.inputs[0].shape[2]))
            except Exception:
                input_shape = (150, 150)

            arr = np.array(pil.resize(input_shape)).astype('float32') / 255.0
            batched = np.expand_dims(arr, axis=0)
            preds = tf_model.predict(batched, verbose=0)
            # normalize preds to 1D probs
            if preds is None:
                return JSONResponse({'error': 'Model produced no output'}, status_code=500)

            # If an alternate (LIME-trained) TF model is available, get its predictions and simple-average the probabilities
            try:
                if alt_tf_model is not None:
                    alt_preds = alt_tf_model.predict(batched, verbose=0)
                    # normalize alt_preds to shape (N, C)
                    if alt_preds is not None:
                        if alt_preds.ndim == 1 or (alt_preds.ndim == 2 and alt_preds.shape[-1] == 1):
                            alt_probs = alt_preds.ravel()
                            if alt_probs.size == 1:
                                alt_probs = np.array([1 - alt_probs[0], alt_probs[0]])
                        else:
                            alt_probs = alt_preds[0]
                        # ensure same length and average
                        try:
                            if alt_probs.shape == preds[0].shape:
                                # use element-wise average of probability vectors
                                probs = (preds[0] + alt_probs) / 2.0 if (preds.ndim > 1) else (preds + alt_probs) / 2.0
                            else:
                                # shapes differ — ignore alt model
                                pass
                        except Exception:
                            pass
            except Exception:
                # ignore alternate model failures — continue with primary model
                pass

            if preds.ndim == 1 or (preds.ndim == 2 and preds.shape[-1] == 1):
                probs = preds.ravel()
                # binary decision heuristic
                if probs.size == 1:
                    probs = np.array([1 - probs[0], probs[0]])
                pred_idx = int(np.argmax(probs))
            else:
                probs = preds[0]
                pred_idx = int(np.argmax(probs))

            label = LABELS.get(str(pred_idx), str(pred_idx))
            confidence = float(probs[pred_idx]) if probs is not None else None

            # (MRI detection already performed earlier)

            # build top-k
            try:
                top_k = []
                k = min(5, probs.shape[-1]) if hasattr(probs, 'shape') else 1
                top_idx = np.argsort(probs)[-k:][::-1]
                for i in top_idx:
                    lab = LABELS.get(str(int(i)), str(int(i)))
                    top_k.append({'label': lab, 'probability': float(probs[int(i)])})
                probs_map = {LABELS.get(str(i), str(i)): float(probs[int(i)]) for i in range(len(probs))}
            except Exception:
                top_k = []
                probs_map = {}

            # compute Grad-CAM using tf-keras-vis if available
            cam_b64 = pil_to_base64(pil)
            try:
                from tf_keras_vis.gradcam import Gradcam
                from tf_keras_vis.utils.scores import CategoricalScore
                from tf_keras_vis.utils.model_modifiers import ReplaceToLinear
                import tensorflow as tf
                import cv2

                score = CategoricalScore([pred_idx])
                model_modifier = ReplaceToLinear()
                penultimate_layer = None
                for layer in reversed(tf_model.layers):
                    try:
                        if hasattr(layer, 'output') and len(layer.output.shape) == 4:
                            penultimate_layer = layer.name
                            break
                    except Exception:
                        continue

                gradcam = Gradcam(tf_model, model_modifier=model_modifier)
                cam = gradcam(score, batched, penultimate_layer=penultimate_layer)
                heatmap = cam[0]
                hm = heatmap - heatmap.min()
                if hm.max() > 0:
                    hm = hm / hm.max()
                hm_resized = cv2.resize(hm, (arr.shape[1], arr.shape[0]))
                heatmap_color = cv2.applyColorMap((hm_resized * 255).astype('uint8'), cv2.COLORMAP_JET)
                heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)
                overlay = (0.4 * heatmap_color / 255.0 + 0.6 * arr).clip(0, 1)
                cam_pil = Image.fromarray((overlay * 255).astype('uint8'))
                cam_b64 = pil_to_base64(cam_pil)
            except Exception:
                # fallback to original image base64
                cam_b64 = pil_to_base64(pil)

            # save into session store (Redis if available, otherwise in-memory)
            session_id = await _get_or_create_session_id(request)
            try:
                if redis_client is not None:
                    s = await _redis_get_session(session_id)
                    s['last_prediction'] = label
                    s['last_confidence'] = confidence
                    await _redis_set_session(session_id, s)
                else:
                    SESSION_STORE.setdefault(session_id, {})['last_prediction'] = label
                    SESSION_STORE.setdefault(session_id, {})['last_confidence'] = confidence
            except Exception as e:
                logging.warning(f"Failed to save prediction to session: {e}")

            # Get comprehensive medical analysis
            medical_analysis = get_tumor_analysis(label, confidence)
            medication_effects = get_medication_side_effects(label)
            lifestyle_recs = get_lifestyle_recommendations(label)

            resp = {
                'model_type': 'tensorflow',
                'is_brain': True,
                'label': label,
                'confidence': confidence,
                'top_k': top_k,
                'probs': probs_map,
                'image_size': {'width': pil.width, 'height': pil.height},
                'preprocessing': {'input_shape': input_shape, 'scale': 'pixel/255.0'},
                'cam_image': cam_b64,
                'session_id': session_id,
                'explanation': None,
                'explanation_messages': [],
                'medical_analysis': medical_analysis,
                'medication_side_effects': medication_effects,
                'lifestyle_recommendations': lifestyle_recs
            }

            # generate a safe explanation (LLM-enhanced if OPENAI configured)
            try:
                label_idx = str(pred_idx) if 'pred_idx' in locals() else None
                label_name = label
                if openai is not None and OPENAI_API_KEY is not None:
                    try:
                        expl = llm_explanation(label_idx, label_name, confidence, top_k, probs_map)
                    except Exception:
                        expl = _rule_explanation(label_name, confidence)
                else:
                    expl = _rule_explanation(label_name, confidence)
                resp['explanation'] = expl
                
                # Split explanation into conversational chat messages
                resp['explanation_messages'] = _split_explanation_to_messages(label, confidence, medical_analysis)
            except Exception:
                resp['explanation'] = _rule_explanation(label, confidence)
                resp['explanation_messages'] = _split_explanation_to_messages(label, confidence, medical_analysis)

            # include which model file was used and any evaluation summary available
            try:
                resp['used_model'] = model_path if model_path is not None else None
                resp['models_evaluation'] = MODELS_EVAL
            except Exception:
                resp['used_model'] = None
                resp['models_evaluation'] = {}

            # add a short list of suggested Q&A (assistant-style answers) about the prediction
            try:
                resp['qa'] = _build_prediction_qa(label, confidence, top_k)
            except Exception:
                resp['qa'] = []

            # persist predict outputs to disk under outputs/<session_id>/
            try:
                out_dir = pathlib.Path('outputs') / session_id
                out_dir.mkdir(parents=True, exist_ok=True)
                # write full JSON
                with open(out_dir / 'predict.json', 'w', encoding='utf-8') as jf:
                    json.dump(resp, jf, ensure_ascii=False, indent=2)
                # write cam image as PNG (decode base64)
                try:
                    cam_bytes = base64.b64decode(cam_b64)
                    with open(out_dir / 'cam.png', 'wb') as imf:
                        imf.write(cam_bytes)
                except Exception:
                    # fallback: save original uploaded image
                    pil.save(out_dir / 'cam.png')
            except Exception:
                # don't fail the request if disk persistence fails
                pass

            # append an assistant message summarizing the prediction into the session history
            try:
                summary_text = f"Prediction: {label} (confidence: {confidence:.4f})"
                try:
                    if redis_client is not None:
                        s = await _redis_get_session(session_id)
                        hist = s.get('history', [])
                        hist.append({'role': 'assistant', 'message': summary_text})
                        s['history'] = hist
                        s['last_prediction'] = label
                        s['last_confidence'] = confidence
                        await _redis_set_session(session_id, s)
                    else:
                        s = SESSION_STORE.setdefault(session_id, {})
                        hist = s.get('history') or []
                        hist.append({'role': 'assistant', 'message': summary_text})
                        s['history'] = hist
                        s['last_prediction'] = label
                        s['last_confidence'] = confidence
                except Exception as e:
                    logging.warning(f"Failed to append assistant message: {e}")
            except Exception:
                pass

            # now create the response and set cookie
            response = JSONResponse(resp)
            response.set_cookie('session_id', session_id, httponly=True)
            return response

        elif torch_model is not None:
            return JSONResponse({'error': 'Torch model serving not implemented in this endpoint'}, status_code=500)
        else:
            return JSONResponse({'error': 'No model available. Place models/model.h5 or models/model.pth'}, status_code=500)

    except Exception as e:
        logging.error(f"Prediction error: {e}", exc_info=True)
        return JSONResponse({'error': f'Prediction failed: {str(e)}'}, status_code=500)





@app.post('/chat')
async def chat(req: Request):
    body = await req.json()
    msg = body.get('message')
    
    # Get or create session ID
    session_id = req.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Fetch last prediction for context
    last_pred = None
    last_conf = None
    if session_id:
        if redis_client is not None:
            s = await _redis_get_session(session_id)
        else:
            s = SESSION_STORE.get(session_id, {})
        last_pred = s.get('last_prediction')
        last_conf = s.get('last_confidence')

    # check global canned QA first (exact normalized match)
    try:
        if msg:
            import re
            nm = re.sub(r"[^a-z0-9\s]", '', msg.lower()).strip()
            nm = re.sub(r"\s+", ' ', nm)
            if nm in GLOBAL_QA:
                reply = GLOBAL_QA[nm]
                # append to session history and persist
                if session_id:
                    entry_user = {'role': 'user', 'message': msg}
                    entry_assistant = {'role': 'assistant', 'message': reply}
                    if redis_client is not None:
                        s = await _redis_get_session(session_id)
                        hist = s.get('history', [])
                        hist.append(entry_user)
                        hist.append(entry_assistant)
                        s['history'] = hist
                        await _redis_set_session(session_id, s)
                    else:
                        s = SESSION_STORE.setdefault(session_id, {})
                        hist = s.get('history') or []
                        hist.append(entry_user)
                        hist.append(entry_assistant)
                        s['history'] = hist
                response = JSONResponse({'reply': reply})
                response.set_cookie('session_id', session_id, httponly=True)
                return response
            # try fuzzy canned answer
            canned = _find_canned_answer(msg)
            if canned:
                reply = canned
                if session_id:
                    entry_user = {'role': 'user', 'message': msg}
                    entry_assistant = {'role': 'assistant', 'message': reply}
                    if redis_client is not None:
                        s = await _redis_get_session(session_id)
                        hist = s.get('history', [])
                        hist.append(entry_user)
                        hist.append(entry_assistant)
                        s['history'] = hist
                        await _redis_set_session(session_id, s)
                    else:
                        s = SESSION_STORE.setdefault(session_id, {})
                        hist = s.get('history') or []
                        hist.append(entry_user)
                        hist.append(entry_assistant)
                        s['history'] = hist
                response = JSONResponse({'reply': reply})
                response.set_cookie('session_id', session_id, httponly=True)
                return response
    except Exception:
        pass

    # prefer LLM if configured
    # Always block obvious PII regardless of LLM configuration
    if _contains_pii(msg):
        logger.info('PII detected in message for session %s', session_id)
        reply = 'I cannot process messages that include personally identifiable information (PII). Please remove such details and try again.'
    else:
        # Apply rate-limiting for chat (LLM or rule-based) to prevent abuse
        allowed = await _llm_check_and_increment(session_id)
        if not allowed:
            logger.info('Rate limit exceeded for session %s', session_id)
            reply = 'Rate limit exceeded. Please try again later.'
        else:
            use_llm = LLM_ENABLED and openai is not None and OPENAI_API_KEY is not None
            if use_llm:
                try:
                    reply = llm_chat(msg, last_pred, last_conf)
                except Exception as e:
                    logger.warning('LLM call failed: %s', e)
                    reply = rule_based_chat(msg, last_pred, last_conf)
            else:
                reply = rule_based_chat(msg, last_pred, last_conf)

    # append to session history and persist
    if session_id:
        entry_user = {'role': 'user', 'message': msg}
        entry_assistant = {'role': 'assistant', 'message': reply}
        if redis_client is not None:
            s = await _redis_get_session(session_id)
            hist = s.get('history', [])
            hist.append(entry_user)
            hist.append(entry_assistant)
            s['history'] = hist
            # keep last_prediction/last_confidence if present
            if last_pred is not None:
                s['last_prediction'] = last_pred
            if last_conf is not None:
                s['last_confidence'] = last_conf
            await _redis_set_session(session_id, s)
        else:
            s = SESSION_STORE.setdefault(session_id, {})
            hist = s.get('history') or []
            hist.append(entry_user)
            hist.append(entry_assistant)
            s['history'] = hist
            # Keep prediction in session
            if last_pred is not None:
                s['last_prediction'] = last_pred
            if last_conf is not None:
                s['last_confidence'] = last_conf

    response = JSONResponse({'reply': reply})
    response.set_cookie('session_id', session_id, httponly=True)
    return response


@app.get('/session')
async def get_session(request: Request):
    """Return the session object for the requesting client (based on cookie)."""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return JSONResponse({'error': 'no session'}, status_code=404)
    if redis_client is not None:
        s = await _redis_get_session(session_id)
    else:
        s = SESSION_STORE.get(session_id, {})
    return JSONResponse({'session_id': session_id, 'session': s})


@app.post('/explain')
async def explain(request: Request):
    """Return comprehensive explanation for the last prediction including tumor details, symptoms, side effects, etc.
    
    Only works for valid brain MRI predictions - rejects invalid images and non-medical images.
    """
    session_id = request.cookies.get('session_id')
    if not session_id:
        return JSONResponse({'error': 'no session'}, status_code=400)

    # rate-limit LLM usage per session
    allowed = await _llm_check_and_increment(session_id)
    if not allowed:
        return JSONResponse({'error': 'rate_limited', 'message': 'Rate limit exceeded. Please try again later.'}, status_code=429)

    # fetch last prediction info from session or outputs file
    if redis_client is not None:
        s = await _redis_get_session(session_id)
    else:
        s = SESSION_STORE.get(session_id, {})

    last_pred = s.get('last_prediction')
    last_conf = s.get('last_confidence')
    top_k = s.get('top_k')
    probs_map = s.get('probs')

    # try to read persisted predict.json for richer context
    try:
        pj = pathlib.Path('outputs') / session_id / 'predict.json'
        if pj.exists():
            with open(pj, 'r', encoding='utf-8') as f:
                pjdata = json.load(f)
                last_pred = last_pred or pjdata.get('label')
                last_conf = last_conf or pjdata.get('confidence')
                top_k = top_k or pjdata.get('top_k')
                probs_map = probs_map or pjdata.get('probs')
    except Exception:
        pass

    if not last_pred:
        return JSONResponse({'error': 'no_prediction', 'message': 'No prior prediction found for this session. Please upload a brain MRI image first.'}, status_code=400)

    # Check if prediction is invalid - only allow valid tumor predictions
    if last_pred.lower().startswith('invalid image'):
        return JSONResponse({'error': 'invalid_image', 'message': 'Invalid image - comprehensive explanation only available for valid brain MRI images.'}, status_code=400)

    # Only allow explanations for actual tumor types or no_tumor
    valid_predictions = ['glioma_tumor', 'meningioma_tumor', 'pituitary_tumor', 'no_tumor']
    if last_pred.lower() not in valid_predictions:
        return JSONResponse({'error': 'invalid_prediction', 'message': 'Invalid prediction type - comprehensive explanation only available for brain tumor classifications.'}, status_code=400)

    # Build comprehensive explanation with all required details
    conf_percent = (last_conf or 0) * 100
    
    # 1. TUMOR PERCENTAGE (Confidence Score)
    tumor_percentage = {
        'confidence': f"{conf_percent:.1f}%",
        'interpretation': f"Model confidence in this prediction is {conf_percent:.1f}%"
    }
    
    # 2. DISEASE INFORMATION - Define for each tumor type
    disease_info = {}
    if 'glioma' in last_pred.lower():
        disease_info = {
            'name': 'Glioma Tumor',
            'description': 'Glioma is a type of brain tumor that originates from glial cells (supportive cells of the brain and nervous system).',
            'types': 'Can be classified as low-grade (slow-growing) or high-grade (aggressive)',
            'prevalence': 'Most common type of primary brain tumor',
            'origin': 'Arises from astrocytes, oligodendrocytes, or ependymal cells'
        }
    elif 'meningioma' in last_pred.lower():
        disease_info = {
            'name': 'Meningioma Tumor',
            'description': 'Meningioma is a tumor arising from the meninges - the protective membranes surrounding the brain and spinal cord.',
            'types': 'Typically benign (non-cancerous) but can be atypical or malignant',
            'prevalence': 'Accounts for about 30% of primary brain tumors',
            'origin': 'Arises from the dura mater, arachnoid mater layers'
        }
    elif 'pituitary' in last_pred.lower():
        disease_info = {
            'name': 'Pituitary Tumor',
            'description': 'Pituitary tumor originates from the pituitary gland - a small gland at the base of the brain that regulates hormones.',
            'types': 'Can be hormone-secreting (functional) or non-secreting (non-functional)',
            'prevalence': 'Accounts for 10-15% of primary brain tumors',
            'origin': 'Arises from pituitary gland cells'
        }
    elif 'no_tumor' in last_pred.lower() or 'no tumor' in last_pred.lower():
        disease_info = {
            'name': 'No Tumor Detected',
            'description': 'The brain MRI scan shows no detectable tumor.',
            'status': 'Normal brain tissue detected',
            'note': 'This is a positive result indicating normal brain structure'
        }
    
    # 3. SYMPTOMS - Define for each tumor type
    symptoms = {}
    if 'glioma' in last_pred.lower():
        symptoms = {
            'common': ['Headaches (often progressive)', 'Seizures', 'Vision or hearing loss', 'Balance and coordination problems', 'Cognitive changes'],
            'severe': ['Weakness or numbness in limbs', 'Difficulty speaking', 'Memory loss', 'Behavioral changes'],
            'note': 'Symptoms depend on tumor location, size, and grade. Not all patients experience symptoms.'
        }
    elif 'meningioma' in last_pred.lower():
        symptoms = {
            'common': ['Headaches', 'Vision problems (especially peripheral)', 'Hearing loss', 'Nausea and vomiting'],
            'severe': ['Weakness in arms or legs', 'Cognitive difficulties', 'Personality changes', 'Loss of balance'],
            'note': 'Many slow-growing meningiomas may not cause symptoms initially.'
        }
    elif 'pituitary' in last_pred.lower():
        symptoms = {
            'hormonal': ['Excessive growth (acromegaly)', 'Excessive milk production', 'Irregular menstruation', 'Sexual dysfunction', 'Fatigue and weakness'],
            'local': ['Headaches', 'Vision loss (especially peripheral)', 'Double vision'],
            'note': 'Symptoms vary based on hormone type and tumor size.'
        }
    elif 'no_tumor' in last_pred.lower() or 'no tumor' in last_pred.lower():
        symptoms = {
            'status': 'No tumor-related symptoms expected',
            'note': 'Normal brain tissue indicates no pathology detected'
        }
    
    # 4. SIDE EFFECTS / TREATMENT SIDE EFFECTS
    side_effects = {}
    if 'glioma' in last_pred.lower():
        side_effects = {
            'surgery': ['Infection risk', 'Brain edema', 'Neurological deficits', 'Memory or speech issues', 'Bleeding'],
            'radiation': ['Hair loss', 'Scalp irritation', 'Fatigue', 'Cognitive changes', 'Secondary cancer risk (long-term)'],
            'chemotherapy': ['Nausea and vomiting', 'Hair loss', 'Bone marrow suppression', 'Infection risk', 'Cognitive effects'],
            'note': 'Side effects vary based on treatment type and individual factors'
        }
    elif 'meningioma' in last_pred.lower():
        side_effects = {
            'surgery': ['Infection', 'Bleeding', 'Brain edema', 'Temporary neurological changes'],
            'radiation': ['Hair loss', 'Fatigue', 'Skin irritation', 'Cognitive changes (rare)'],
            'observation': ['Minimal side effects with monitoring approach'],
            'note': 'Many meningiomas can be managed conservatively with observation'
        }
    elif 'pituitary' in last_pred.lower():
        side_effects = {
            'medication': ['Nausea', 'Fatigue', 'Dizziness', 'Hormonal imbalances'],
            'surgery': ['Bleeding', 'Infection', 'Cerebrospinal fluid leak', 'Hormonal imbalances', 'Vision changes'],
            'radiation': ['Fatigue', 'Hair loss', 'Cognitive changes (rare)', 'Secondary hormone deficiencies'],
            'note': 'Specific side effects depend on treatment approach'
        }
    
    # 5. DOCTOR RECOMMENDATION
    doctor_recommendation = {
        'urgency': 'Schedule appointment with a neurologist or neurosurgeon',
        'recommendations': [
            '1. Get professional medical evaluation from a qualified neurologist or radiologist',
            '2. Share this MRI scan and analysis with your healthcare provider',
            '3. Discuss treatment options if needed (surgery, radiation, medication, monitoring)',
            f'4. Get a second opinion from another medical specialist',
            '5. Ask about follow-up imaging schedule',
            '6. Discuss symptom management strategies',
            '7. Create a treatment plan with your medical team'
        ],
        'important_note': '⚠️ This is an AI-generated prediction and NOT a medical diagnosis. Professional medical evaluation is ESSENTIAL for proper diagnosis and treatment planning.',
        'emergency': 'Seek emergency care if experiencing severe headaches, loss of consciousness, severe vision loss, or difficulty breathing.'
    }
    
    # Compile comprehensive explanation with better formatting
    comprehensive_explanation = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          COMPREHENSIVE BRAIN MRI ANALYSIS REPORT                            ║
║                     Professional Medical Analysis                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 1. TUMOR DETECTION CONFIDENCE (Model Accuracy)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Confidence Score: {tumor_percentage['confidence']}
   
   {tumor_percentage['interpretation']}
   
   • What this means: The AI model has analyzed your brain MRI and is 
     {conf_percent:.1f}% confident in its assessment.
   • Higher percentage = Higher certainty in the prediction
   • However, this is NOT a medical diagnosis - professional evaluation needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔬 2. DISEASE INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Detected Condition: {disease_info.get('name', 'Unknown')}
   
   Description:
   {disease_info.get('description', 'N/A')}
   
   {f"Classification: {disease_info.get('types', disease_info.get('status', 'N/A'))}" if 'types' in disease_info or 'status' in disease_info else ''}
   {f"Source/Origin: {disease_info.get('origin', '')}" if 'origin' in disease_info else ''}
   {f"Prevalence: {disease_info.get('prevalence', '')}" if 'prevalence' in disease_info else ''}
   
   Key Information:
   {format_disease_details(disease_info)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  3. COMMON SYMPTOMS & WARNING SIGNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{format_symptoms_detailed(symptoms)}

   Important Note:
   • Not all patients experience all symptoms
   • Symptoms depend on tumor location, size, and type
   • Presence of symptoms doesn't confirm diagnosis
   • Absence of symptoms doesn't mean it's not serious

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💊 4. POTENTIAL SIDE EFFECTS & TREATMENT CONSIDERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{format_side_effects_detailed(side_effects)}

   Treatment Selection:
   • Treatment choice depends on: tumor size, location, grade, patient age, 
     overall health, and patient preferences
   • Multiple treatment options may be available
   • Your doctor will recommend the best approach for your specific case

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏥 5. URGENT: DOCTOR VISIT RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   RECOMMENDED ACTION: {doctor_recommendation['urgency']}
   
   PRIORITY TASKS:
   ✓ {doctor_recommendation['recommendations'][0] if len(doctor_recommendation['recommendations']) > 0 else ''}
   ✓ {doctor_recommendation['recommendations'][1] if len(doctor_recommendation['recommendations']) > 1 else ''}
   ✓ {doctor_recommendation['recommendations'][2] if len(doctor_recommendation['recommendations']) > 2 else ''}
   ✓ {doctor_recommendation['recommendations'][3] if len(doctor_recommendation['recommendations']) > 3 else ''}
   ✓ {doctor_recommendation['recommendations'][4] if len(doctor_recommendation['recommendations']) > 4 else ''}
   ✓ {doctor_recommendation['recommendations'][5] if len(doctor_recommendation['recommendations']) > 5 else ''}
   ✓ {doctor_recommendation['recommendations'][6] if len(doctor_recommendation['recommendations']) > 6 else ''}
   
   SPECIALIST TO CONSULT:
   • Neurologist (specialist in nervous system disorders)
   • Neurosurgeon (if surgery is considered)
   • Oncologist (if cancer-related)
   • Radiologist (for imaging interpretation)
   
   WHAT TO BRING TO YOUR APPOINTMENT:
   • This MRI scan and analysis
   • Any previous medical records
   • List of current medications
   • Family medical history
   • Symptom diary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 EMERGENCY WARNING SIGNS - SEEK IMMEDIATE MEDICAL ATTENTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you experience ANY of the following, go to the emergency room immediately:
   • Severe, sudden headache (worst headache of your life)
   • Loss of consciousness or fainting
   • Severe vision loss or eye pain
   • Difficulty breathing or swallowing
   • Severe weakness or paralysis
   • Uncontrollable seizures
   • Severe confusion or inability to communicate
   • Significant change in mental status
   • Difficulty walking or loss of balance

Call Emergency Services (911 or your local emergency number) if these occur.

╔══════════════════════════════════════════════════════════════════════════════╗
║                          IMPORTANT DISCLAIMERS                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⚠️  CRITICAL LEGAL NOTICE:                                                   ║
║                                                                              ║
║ • This analysis is AI-generated and is NOT a medical diagnosis              ║
║ • It is NOT a substitute for professional medical evaluation                ║
║ • AI predictions can be incorrect - professional confirmation is ESSENTIAL  ║
║ • Only a qualified medical professional can provide a diagnosis             ║
║ • Treatment decisions MUST be made with your healthcare provider            ║
║ • Do NOT delay seeking medical care based on this analysis                  ║
║ • Always consult with a licensed physician or medical specialist            ║
║ • This information is for educational purposes only                         ║
║                                                                              ║
║ Your health and safety are paramount. Seek professional medical advice.     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Report Type: Comprehensive AI-Assisted Analysis
Confidence Level: {conf_percent:.1f}%
"""
    
    # Store comprehensive report in session for future reference
    try:
        entry = {'role': 'assistant', 'message': f"Comprehensive Explanation Report\n\n{comprehensive_explanation}"}
        if redis_client is not None:
            s = await _redis_get_session(session_id)
            hist = s.get('history', [])
            hist.append(entry)
            s['history'] = hist
            await _redis_set_session(session_id, s)
        else:
            s = SESSION_STORE.setdefault(session_id, {})
            hist = s.get('history') or []
            hist.append(entry)
            s['history'] = hist
    except Exception as e:
        logger.error(f"Failed to store explain in history: {e}")
    
    # Return detailed explanation as individual colored sections
    detailed_sections = [
        {
            'type': 'analysis',
            'title': '📊 TUMOR DETECTION CONFIDENCE',
            'text': f"""Confidence Score: {tumor_percentage['confidence']}

{tumor_percentage['interpretation']}

• What this means: The AI model has analyzed your brain MRI and is {conf_percent:.1f}% confident in its assessment.
• Higher percentage = Higher certainty in the prediction
• However, this is NOT a medical diagnosis - professional evaluation needed"""
        },
        {
            'type': 'disease',
            'title': '🔬 DISEASE INFORMATION',
            'text': f"""Detected Condition: {disease_info.get('name', 'Unknown')}

Description:
{disease_info.get('description', 'N/A')}

{f"Classification: {disease_info.get('types', disease_info.get('status', 'N/A'))}" if 'types' in disease_info or 'status' in disease_info else ''}
{f"Source/Origin: {disease_info.get('origin', '')}" if 'origin' in disease_info else ''}
{f"Prevalence: {disease_info.get('prevalence', '')}" if 'prevalence' in disease_info else ''}"""
        },
        {
            'type': 'symptoms',
            'title': '⚠️ COMMON SYMPTOMS & WARNING SIGNS',
            'text': f"""{format_symptoms_detailed(symptoms)}

Important Note:
• Not all patients experience all symptoms
• Symptoms depend on tumor location, size, and type
• Presence of symptoms doesn't confirm diagnosis
• Absence of symptoms doesn't mean it's not serious"""
        },
        {
            'type': 'treatment',
            'title': '💊 POTENTIAL SIDE EFFECTS & TREATMENT',
            'text': f"""{format_side_effects_detailed(side_effects)}

Treatment Selection:
• Treatment choice depends on: tumor size, location, grade, patient age, overall health, and patient preferences
• Multiple treatment options may be available
• Your doctor will recommend the best approach for your specific case"""
        },
        {
            'type': 'recommendation',
            'title': '🏥 DOCTOR VISIT RECOMMENDATIONS',
            'text': f"""RECOMMENDED ACTION: {doctor_recommendation['urgency']}

PRIORITY TASKS:
✓ Get professional medical evaluation from a qualified neurologist or radiologist
✓ Share this MRI scan and analysis with your healthcare provider
✓ Discuss treatment options if needed (surgery, radiation, medication, monitoring)
✓ Get a second opinion from another medical specialist
✓ Ask about follow-up imaging schedule
✓ Discuss symptom management strategies
✓ Create a treatment plan with your medical team

SPECIALIST TO CONSULT:
• Neurologist (specialist in nervous system disorders)
• Neurosurgeon (if surgery is considered)
• Oncologist (if cancer-related)
• Radiologist (for imaging interpretation)

⚠️ CRITICAL: This is an AI-generated prediction and NOT a medical diagnosis. Professional medical evaluation is ESSENTIAL."""
        }
    ]
    
    return JSONResponse({'explanation_sections': detailed_sections})


def format_disease_details(info):
    """Format disease information with better detail."""
    details = []
    if 'types' in info:
        details.append(f"   • Type: {info['types']}")
    if 'origin' in info:
        details.append(f"   • Origin: {info['origin']}")
    if 'prevalence' in info:
        details.append(f"   • Prevalence: {info['prevalence']}")
    if 'status' in info:
        details.append(f"   • Status: {info['status']}")
    if 'note' in info:
        details.append(f"   • Note: {info['note']}")
    return '\n'.join(details) if details else "   • No additional details available"


def format_symptoms_detailed(symptoms):
    """Format symptoms with detailed organization."""
    if not symptoms or len(symptoms) == 0:
        return "   No specific symptoms expected for this condition."
    
    result = []
    if 'common' in symptoms:
        result.append("   COMMON SYMPTOMS:")
        for item in symptoms.get('common', []):
            result.append(f"      □ {item}")
    
    if 'severe' in symptoms:
        result.append("\n   SEVERE/URGENT SYMPTOMS:")
        for item in symptoms.get('severe', []):
            result.append(f"      □ {item}")
    
    if 'hormonal' in symptoms:
        result.append("\n   HORMONAL SYMPTOMS:")
        for item in symptoms.get('hormonal', []):
            result.append(f"      □ {item}")
    
    if 'local' in symptoms:
        result.append("\n   LOCAL SYMPTOMS:")
        for item in symptoms.get('local', []):
            result.append(f"      □ {item}")
    
    if 'status' in symptoms:
        result.append(f"\n   STATUS: {symptoms['status']}")
    
    if 'note' in symptoms:
        result.append(f"\n   {symptoms['note']}")
    
    return '\n'.join(result) if result else "   No specific symptoms listed"


def format_side_effects_detailed(effects):
    """Format side effects with detailed organization."""
    if not effects or len(effects) == 0:
        return "   • No treatment side effects expected for this condition."
    
    result = []
    
    if 'surgery' in effects:
        result.append("   SURGICAL PROCEDURE SIDE EFFECTS:")
        for item in effects.get('surgery', []):
            result.append(f"      • {item}")
    
    if 'radiation' in effects:
        result.append("\n   RADIATION THERAPY SIDE EFFECTS:")
        for item in effects.get('radiation', []):
            result.append(f"      • {item}")
    
    if 'chemotherapy' in effects:
        result.append("\n   CHEMOTHERAPY SIDE EFFECTS:")
        for item in effects.get('chemotherapy', []):
            result.append(f"      • {item}")
    
    if 'medication' in effects:
        result.append("\n   MEDICATION SIDE EFFECTS:")
        for item in effects.get('medication', []):
            result.append(f"      • {item}")
    
    if 'observation' in effects:
        result.append("\n   MONITORING APPROACH:")
        for item in effects.get('observation', []):
            result.append(f"      • {item}")
    
    if 'note' in effects:
        result.append(f"\n   Note: {effects['note']}")
    
    return '\n'.join(result) if result else "   • No specific side effects listed"


def format_side_effects(effects):
    """Helper to format side effects by category."""
    result = []
    for category, details in effects.items():
        if category != 'note':
            result.append(f"{category.upper().replace('_', ' ')}:")
            if isinstance(details, list):
                for item in details:
                    result.append(f"  • {item}")
            else:
                result.append(f"  {details}")
    if 'note' in effects:
        result.append(f"\nNote: {effects['note']}")
    return '\n'.join(result)




















@app.get('/predict/batch')
async def predict_batch(include_qa: bool = False):
    """Return batch prediction results in the same schema as the `/predict` response.

    Reads `outputs/batch/batch_predictions.json` and enriches each record with
    explanation, medical analysis, medication side effects, lifestyle recommendations,
    and optional QA (controlled by `include_qa` query param).
    """
    pj = pathlib.Path('outputs') / 'batch' / 'batch_predictions.json'
    if not pj.exists():
        return JSONResponse({'error': 'no_batch_predictions', 'message': 'No batch predictions file found under outputs/batch/'}, status_code=404)
    try:
        with open(pj, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return JSONResponse({'error': 'failed_read', 'message': str(e)}, status_code=500)

    out_list = []
    for rec in (data if isinstance(data, list) else [data]):
        label = rec.get('label')
        confidence = float(rec.get('confidence') or 0.0)
        top_k = rec.get('top_k', [])
        probs_map = rec.get('probs', {})

        # safe explanation (LLM if available, otherwise rule-based)
        try:
            label_idx = None
            for k, v in LABELS.items():
                if v == label:
                    label_idx = k
                    break
            if openai is not None and OPENAI_API_KEY is not None:
                try:
                    expl = llm_explanation(label_idx or '', label, confidence, top_k, probs_map)
                except Exception:
                    expl = _rule_explanation(label, confidence)
            else:
                expl = _rule_explanation(label, confidence)
        except Exception:
            expl = _rule_explanation(label, confidence)

        # medical knowledge enrichment
        try:
            medical_analysis = get_tumor_analysis(label, confidence)
        except Exception:
            medical_analysis = {}
        try:
            medication_effects = get_medication_side_effects(label)
        except Exception:
            medication_effects = {}
        try:
            lifestyle_recs = get_lifestyle_recommendations(label)
        except Exception:
            lifestyle_recs = []

        # build QA if requested (function handles LLM availability)
        try:
            qa = _build_prediction_qa(label, confidence, top_k) if include_qa else []
        except Exception:
            qa = []

        out_rec = {
            'model_type': 'tensorflow',
            'is_brain': True,
            'label': label,
            'confidence': confidence,
            'top_k': top_k,
            'probs': probs_map,
            'image_size': rec.get('image_size'),
            'preprocessing': rec.get('preprocessing'),
            'cam_image': rec.get('cam_image'),
            'explanation': expl,
            'medical_analysis': medical_analysis,
            'medication_side_effects': medication_effects,
            'lifestyle_recommendations': lifestyle_recs,
            'qa': qa,
            'used_model': model_path if 'model_path' in globals() else None,
            'models_evaluation': MODELS_EVAL or {}
        }

        out_list.append(out_rec)

    return JSONResponse({'count': len(out_list), 'predictions': out_list})


# Mount the frontend static files
app.mount('/frontend', StaticFiles(directory='frontend'), name='frontend')


if __name__ == '__main__':
    import uvicorn
    print("🚀 Starting Neuro ASSIST Server...")
    print("📍 Homepage with 3D animations: http://localhost:8010")
    print("🎯 Gradio interface: http://localhost:8010/frontend/neuro_assist.html")
    print("Press Ctrl+C to stop the server")
    uvicorn.run('fastapi_app:app', host='0.0.0.0', port=8010, reload=False)