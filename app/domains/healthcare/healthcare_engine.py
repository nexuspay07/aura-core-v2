class HealthcareEngine:
    def __init__(self):
        self.symptom_database = {
            "chest pain": {
                "info": "Chest pain can have many causes, including muscle strain, acid reflux, anxiety, or heart-related conditions.",
                "action": "Seek urgent medical attention immediately, especially if severe, sudden, or associated with shortness of breath, sweating, nausea, or pain spreading to the arm, back, or jaw.",
                "urgency": "high"
            },
            "headache": {
                "info": "Headaches are common and can result from stress, dehydration, poor sleep, illness, or other factors.",
                "action": "Rest, hydrate, and monitor symptoms. Seek medical attention if severe, sudden, persistent, or associated with weakness, confusion, or vision changes.",
                "urgency": "medium"
            },
            "fever": {
                "info": "Fever is often a sign that the body is fighting an infection or inflammation.",
                "action": "Rest, hydrate, and monitor temperature. Seek medical care if the fever is very high, persistent, or associated with breathing difficulty, confusion, or dehydration.",
                "urgency": "medium"
            },
            "cough": {
                "info": "Cough may result from infection, irritation, allergies, or respiratory conditions.",
                "action": "Monitor duration and severity. Seek medical care if severe, persistent, associated with chest pain, breathing difficulty, or blood.",
                "urgency": "medium"
            },
            "fatigue": {
                "info": "Fatigue can be caused by stress, poor sleep, infection, nutritional issues, or other health conditions.",
                "action": "Rest, hydrate, and review sleep, nutrition, and stress. Seek medical evaluation if persistent, worsening, or associated with other concerning symptoms.",
                "urgency": "low"
            },
            "shortness of breath": {
                "info": "Shortness of breath can be caused by respiratory, cardiac, anxiety-related, or other serious conditions.",
                "action": "Seek urgent medical attention immediately, especially if sudden, severe, worsening, or associated with chest pain, bluish lips, confusion, or fainting.",
                "urgency": "high"
            },
            "dizziness": {
                "info": "Dizziness may be caused by dehydration, low blood pressure, inner ear issues, infection, or other conditions.",
                "action": "Rest, hydrate, and avoid driving until symptoms improve. Seek medical attention if severe, recurring, or associated with chest pain, fainting, weakness, or speech changes.",
                "urgency": "medium"
            }
        }

        self.disclaimer = (
            "⚠️ This information is for educational purposes only and is not medical advice. "
            "Please consult a licensed healthcare professional for diagnosis or treatment."
        )

    def detect_symptoms(self, message: str):
        message_lower = message.lower()
        detected = []

        for symptom, data in self.symptom_database.items():
            if symptom in message_lower:
                detected.append({
                    "name": symptom,
                    "info": data["info"],
                    "action": data["action"],
                    "urgency": data["urgency"]
                })

        return detected

    def get_overall_urgency(self, detected_symptoms: list):
        if not detected_symptoms:
            return "unknown"

        if any(item["urgency"] == "high" for item in detected_symptoms):
            return "high"
        if any(item["urgency"] == "medium" for item in detected_symptoms):
            return "medium"
        return "low"

    def build_response(self, message: str):
        detected = self.detect_symptoms(message)

        if not detected:
            return {
                "domain": "healthcare",
                "summary": (
                    "AURA did not detect a specific known symptom from your message. "
                    "Please describe the symptom, how long it has been happening, how severe it is, "
                    "and whether there are any other symptoms."
                ),
                "urgency": "unknown",
                "symptoms": [],
                "guidance": [
                    "Describe the main symptom clearly",
                    "Include duration and severity",
                    "Mention any additional symptoms",
                    "Consult a licensed healthcare professional for medical advice"
                ],
                "disclaimer": self.disclaimer
            }

        primary = detected[0]
        urgency = self.get_overall_urgency(detected)

        return {
            "domain": "healthcare",
            "summary": f"AURA detected the symptom '{primary['name']}'. {primary['info']}",
            "urgency": urgency,
            "symptoms": detected,
            "guidance": [item["action"] for item in detected[:3]],
            "disclaimer": self.disclaimer
        }

    # backward-compatible alias
    def process(self, message: str):
        return self.build_response(message)


healthcare_engine = HealthcareEngine()