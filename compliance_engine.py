import os
import json
from llm_router import LLMRouter  # pyre-ignore

class ComplianceEngine:
    def __init__(self, model="llama-3.3-70b-versatile"):
        self.router = LLMRouter(primary_groq_model=model)

    def check_compliance(self, script, title):
        """Evaluates script/title against YouTube and TikTok guidelines using LLM."""
        
        system_prompt = (
            "You are a Content Safety Auditor for YouTube and TikTok. "
            "Analyze the provided script and title for violations of community guidelines: "
            "Graphic violence, Hate speech, Harassment, Misinformation, or Harmful behavior. "
            "Return a JSON object: {\"status\": \"Compliant\"|\"Flagged\", \"risk_level\": \"Low\"|\"Medium\"|\"High\", \"issues\": [], \"recommendation\": \"\"}"
        )
        
        user_prompt = f"Title: {title}\nScript: {script}"

        response = self.router.route_request(system_prompt, user_prompt, response_format="json")
        if response:
            try:
                return json.loads(response)
            except Exception as e:
                print(f"WARN: Failed to parse Compliance JSON: {e}")

        # Final Fallback: Keyword matching if LLMs fail
        restricted = ["violence", "hate", "scam", "harmful"]
        found = [w for w in restricted if w in (title + script).lower()]
        return {
            "status": "Flagged" if found else "Compliant",
            "risk_level": "Medium" if found else "Low",
            "issues": [f"Keyword Match: {w}" for w in found],
            "recommendation": "LLM Check failed. Manual review required."
        }

    def rewrite_for_compliance(self, script, issues):
        """Uses the LLM to rewrite a flagged script to be compliant."""
        system_prompt = (
            "You are an expert script editor. Your task is to rewrite the provided script "
            "to resolve the following compliance issues: " + ", ".join(issues) + ". "
            "Ensure the final script is strictly compliant with YouTube and TikTok community guidelines "
            "while maintaining the original educational or historical value. "
            "Do not remove necessary historical facts, but rephrase them to avoid gore/graphic/harmful/sexualizing/misinformation/disinformation/etc descriptions."
        )
        user_prompt = f"Original Script: {script}"

        response = self.router.route_request(system_prompt, user_prompt, response_format="text")
        if response:
            return response

        return None

if __name__ == "__main__":
    engine = ComplianceEngine()
    # print(engine.check_compliance("This is a test script.", "Test Title"))
