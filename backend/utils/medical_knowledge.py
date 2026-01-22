def get_tumor_analysis(label, conf):
    """Provide analysis based on predicted tumor type."""
    base_analysis = {
        "name": label,
        "confidence": f"{conf*100:.1f}%",
        "description": f"Detected {label} with {conf*100:.1f}% confidence.",
        "recommendations": ["Consult a neurologist immediately.", "Schedule MRI for confirmation."]
    }
    
    # Add symptoms/side effects
    symptoms = get_tumor_symptoms(label)
    if symptoms:
        base_analysis["symptoms"] = symptoms
    
    return base_analysis

def get_tumor_symptoms(label):
    """Get common symptoms for the tumor type."""
    symptoms = {
        "Glioma": ["Headaches", "Seizures", "Nausea", "Vision changes", "Weakness on one side of the body"],
        "Meningioma": ["Headaches", "Seizures", "Vision problems", "Hearing loss", "Weakness"],
        "Pituitary": ["Headaches", "Vision changes", "Hormonal imbalances", "Fatigue", "Weight changes"],
        "notumor": []
    }
    return symptoms.get(label, ["General neurological symptoms; consult a doctor."])

def get_medication_side_effects(label):
    """Get side effects for medications related to the tumor type."""
    side_effects = {
        "Glioma": ["Nausea", "Fatigue", "Hair loss"],
        "Meningioma": ["Headache", "Seizures"],
        "Pituitary": ["Hormonal imbalances", "Vision changes"]
    }
    return side_effects.get(label, [])

def get_lifestyle_recommendations(label):
    """Get lifestyle recommendations."""
    recommendations = {
        "Glioma": ["Maintain healthy diet", "Regular exercise", "Avoid smoking"],
        "Meningioma": ["Stress management", "Adequate sleep"],
        "Pituitary": ["Monitor hormone levels", "Balanced nutrition"]
    }
    return recommendations.get(label, [])