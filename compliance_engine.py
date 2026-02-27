class ComplianceEngine:
    def __init__(self):
        # List of sensitive/restricted keywords for YouTube and TikTok
        self.restricted_keywords = [
            "violence", "hate", "scam", "clickbait", # Add more as needed
        ]

    def check_compliance(self, script, title):
        """Checks if the script or title violates basic policy rules."""
        violations = []
        full_text = f"{title} {script}".lower()
        
        for word in self.restricted_keywords:
            if word in full_text:
                violations.append(f"Restricted Keyword Found: {word}")
        
        if len(violations) == 0:
            return {"status": "Compliant", "issues": []}
        else:
            return {"status": "Flagged", "issues": violations}

if __name__ == "__main__":
    engine = ComplianceEngine()
    # result = engine.check_compliance("This is a peaceful video.", "History Vlog")
    # print(result)
