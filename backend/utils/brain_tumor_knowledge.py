def get_tumor_info(label):
    """Get detailed information about the tumor type."""
    info = {
        "Glioma": {
            "description": "A type of tumor that starts in the glial cells of the brain.",
            "symptoms": ["Headaches", "Seizures", "Cognitive changes"],
            "treatment": ["Surgery", "Radiation", "Chemotherapy"]
        },
        "Meningioma": {
            "description": "A tumor that arises from the meninges.",
            "symptoms": ["Headaches", "Vision problems", "Seizures"],
            "treatment": ["Observation", "Surgery", "Radiation"]
        },
        "Pituitary": {
            "description": "Tumor in the pituitary gland.",
            "symptoms": ["Hormonal issues", "Vision changes", "Headaches"],
            "treatment": ["Medication", "Surgery", "Radiation"]
        }
    }
    return info.get(label, {"description": "Unknown tumor type"})

def answer_question(question):
    """Answer questions about brain tumors."""
    question = question.lower()
    if "symptoms" in question:
        return "Common symptoms include headaches, seizures, and cognitive changes."
    elif "treatment" in question:
        return "Treatment options include surgery, radiation, and chemotherapy."
    elif "prevention" in question:
        return "There are no known prevention methods, but maintaining a healthy lifestyle helps."
    else:
        return "Please consult a medical professional for specific advice."