import os
import json
import re
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# Load labels if available
LABELS = {}
if os.path.exists('models/labels.json'):
    with open('models/labels.json', 'r', encoding='utf-8') as f:
        LABELS = json.load(f)

# Simple global QA (from fastapi_app.py)
GLOBAL_QA = {
    "what is this": "This is a brain tumor detection assistant.",
    "how does it work": "Upload a brain MRI image for analysis using AI models.",
    "is this accurate": "This is for research purposes only; consult a doctor for medical advice.",
}

try:
    from medical_knowledge import get_tumor_analysis
    HAS_MEDICAL_KB = True
except ImportError:
    HAS_MEDICAL_KB = False
    def get_tumor_analysis(label, conf):
        return {"name": label, "confidence": f"{conf*100:.1f}%", "description": f"Detected {label} with {conf*100:.1f}% confidence.", "recommendations": ["Consult a doctor."]}

HAS_BRAIN_TUMOR_KB = False  # Set to True if available

def rule_based_chat(message, last_pred=None, last_conf=None):
    msg = message or ''
    # check global QA exact matches first
    nm = re.sub(r"[^a-z0-9\s]", '', msg.lower()).strip()
    nm = re.sub(r"\s+", ' ', nm)
    if nm in GLOBAL_QA:
        return GLOBAL_QA[nm]
    msg = msg.lower()
    
    # Check for invalid image first
    if last_pred and last_pred.lower().startswith('invalid image'):
        return 'Invalid image'
    
    # Try enhanced brain tumor knowledge base only for valid predictions
    if HAS_BRAIN_TUMOR_KB and last_pred and not last_pred.lower().startswith('invalid'):
        answer = answer_question(message)
        if "specific question" not in answer.lower() or len(answer) > 100:
            return answer
    
    # concise rule-based responses - only about prediction
    if last_pred is None:
        return 'No prediction available. Upload a valid brain MRI image to run inference.'
    # Check for greetings
    if any(word in msg.lower() for word in ['hi', 'hello', 'hey', 'greetings']):
        return 'Hi! What can I help you with? Please upload a brain MRI image for analysis.'
    # Only answer prediction-related questions
    if 'prediction' in msg or 'result' in msg:
        if last_pred and (last_pred.lower().startswith('error') or 'invalid' in last_pred.lower()):
            return "No prediction available. Please upload a valid brain MRI image."
        elif last_pred and last_pred.lower() == 'notumor':
            return f"Prediction: No tumor detected (confidence {last_conf:.2f}). There is no tumor present."
        else:
            analysis = get_tumor_analysis(last_pred, last_conf)
            return f"Prediction: {analysis['description']}"
    if 'explain' in msg or 'why' in msg or 'what' in msg or 'details' in msg or 'image' in msg:
        if last_pred and (last_pred.lower().startswith('error') or 'invalid' in last_pred.lower()):
            return "No valid prediction available. Please upload a correct brain MRI image for analysis."
        elif last_pred and last_pred.lower() == 'notumor':
            return "The image shows a normal brain MRI scan with no signs of tumor. There is no tumor present."
        elif HAS_MEDICAL_KB and last_pred:
            analysis = get_tumor_analysis(last_pred, last_conf)
            details = f"The image indicates a {analysis['name']} tumor with {analysis['confidence']} confidence. {analysis['description']}"
            if 'symptoms' in analysis:
                details += f" Common symptoms/side effects: {', '.join(analysis['symptoms'])}."
            details += f" Recommendations: {'; '.join(analysis['recommendations'])}."
            return details
        else:
            return f'The image suggests a {last_pred} with {last_conf:.2f} confidence. Please consult a medical professional for accurate diagnosis.'
    if 'tumor' in msg or 'brain' in msg or 'symptom' in msg or 'treatment' in msg:
        if last_pred and (last_pred.lower().startswith('error') or 'invalid' in last_pred.lower()):
            return "Please upload a valid brain MRI image to discuss tumor-related information."
        elif last_pred and last_pred.lower() == 'notumor':
            return 'No tumor detected. The image shows no signs of brain tumor.'
        else:
            return 'Based on the prediction, this appears to be a brain tumor. Symptoms may include headaches, seizures, or neurological changes. Treatment depends on type and grade; consult a specialist.'
    # For any other questions, restrict to prediction info
    return 'I can only provide information about the current prediction. Ask about the result, explanation, or tumor information.'

def llm_chat(message: str, last_pred: str = None, last_conf: float = None) -> str:
    """Call OpenAI ChatCompletion to answer the user's message, using last prediction as context."""
    if not OPENAI_AVAILABLE or OPENAI_API_KEY is None:
        raise RuntimeError("OpenAI not configured")

    # Strong system prompt enforcing non-diagnostic, safety-first behavior and prediction-only responses
    system_prompt = (
        "You are a clinical assistant that ONLY answers questions about the current brain tumor prediction. "
        "Do NOT answer general medical questions, diagnoses, or advice outside the prediction context. "
        "Respond in the same language as the user's question (English or Telugu). "
        "If asked about anything else, say you can only provide information about the current prediction. "
        "Do NOT provide medical diagnoses or definitive clinical advice; if the user asks for a diagnosis, refuse and recommend consulting a licensed medical professional."
    )

    context = "" if last_pred is None else f"Last model prediction: {last_pred} (confidence: {last_conf:.2f})."
    user_content = context + "\nUser question: " + message

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
            max_tokens=400,
            temperature=0.2,
        )
        return resp['choices'][0]['message']['content'].strip()
    except Exception as e:
        # bubble up a clear error to caller
        raise RuntimeError(f"OpenAI request failed: {e}")

def chat_response(message, last_pred=None, last_conf=None):
    use_llm = OPENAI_AVAILABLE and OPENAI_API_KEY is not None
    if use_llm:
        try:
            return llm_chat(message, last_pred, last_conf)
        except Exception as e:
            print(f"LLM failed: {e}, falling back to rule-based.")
            return rule_based_chat(message, last_pred, last_conf)
    else:
        return rule_based_chat(message, last_pred, last_conf)

if __name__ == "__main__":
    print("Brain Tumor Detection Chat Assistant")
    print("Type 'quit' to exit.")
    last_pred = None
    last_conf = None
    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break
        response = chat_response(user_input, last_pred, last_conf)
        print(f"Assistant: {response}")
        # In a real app, update last_pred and last_conf from predictions