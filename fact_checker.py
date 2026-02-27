import os
import requests
import time
import random
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class FactChecker:
    def __init__(self, model="llama-3.3-70b-versatile"):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
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

    def verify_script(self, script, category="History"):
        """Cross-references script content using available LLMs. Hierarchy: Groq -> OpenRouter -> Ollama."""
        
        system_prompt = f"You are an expert fact-checker specializing in {category}. Your job is to find any inaccuracies in the provided script and provide corrections."
        user_prompt = f"Please review the following script for accuracy:\n\n{script}"

        # 1. Try Groq
        if self.groq_client:
            for current_model in [self.model_name, "llama-3.1-8b-instant"]:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model=current_model,
                    )
                    return chat_completion.choices[0].message.content
                except Exception as e:
                    print(f"ERROR: FactChecker Groq {current_model} failed: {e}.")

        # 2. Try OpenRouter
        if self.openrouter_client:
            try:
                fallback_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
                response = self.openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=4000
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"ERROR: FactChecker OpenRouter failed: {e}. Falling back...")

        # 3. Try Ollama
        try:
            ollama_response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False},
                timeout=30
            )
            if ollama_response.status_code == 200:
                return ollama_response.json().get("response", "")
        except: pass

        return "Error: Could not verify script with any provider."

if __name__ == "__main__":
    checker = FactChecker()
