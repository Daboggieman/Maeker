import os
from groq import Groq  # type: ignore
from openai import OpenAI  # type: ignore
from dotenv import load_dotenv  # type: ignore

load_dotenv()

class ComplianceEngine:
    def __init__(self, model="llama-3.3-70b-versatile"):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.model_name = model
        
        # Initialize Clients
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
        else:
            self.groq_client = None

        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key
            )
        else:
            self.openrouter_client = None

    def check_compliance(self, script, title):
        """Evaluates script/title against YouTube and TikTok guidelines using LLM."""
        
        system_prompt = (
            "You are a Content Safety Auditor for YouTube and TikTok. "
            "Analyze the provided script and title for violations of community guidelines: "
            "Graphic violence, Hate speech, Harassment, Misinformation, or Harmful behavior. "
            "Return a JSON object: {\"status\": \"Compliant\"|\"Flagged\", \"risk_level\": \"Low\"|\"Medium\"|\"High\", \"issues\": [], \"recommendation\": \"\"}"
        )
        
        user_prompt = f"Title: {title}\nScript: {script}"

        # 1. Try Groq
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model_name,
                    response_format={"type": "json_object"}
                )
                import json
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                print(f"WARN: Compliance LLM (Groq) failed: {e}")

        # 2. Try OpenRouter Fallback
        if self.openrouter_client:
            try:
                fallback_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
                response = self.openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                # Parse loosely if JSON mode isn't guaranteed
                content = response.choices[0].message.content
                import json
                # Try to extract JSON if it's wrapped in markers
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                return json.loads(content)
            except Exception as e:
                print(f"WARN: Compliance LLM (OpenRouter) failed: {e}")

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

        # 1. Try Groq
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model_name
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"WARN: Compliance Rewrite (Groq) failed: {e}")

        # 2. Try OpenRouter Fallback
        if self.openrouter_client:
            try:
                fallback_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
                response = self.openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"WARN: Compliance Rewrite (OpenRouter) failed: {e}")

        return None

if __name__ == "__main__":
    engine = ComplianceEngine()
    # print(engine.check_compliance("This is a test script.", "Test Title"))
