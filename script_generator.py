import os
import requests
import time
import random
from groq import Groq
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class ScriptGenerator:
    def __init__(self, model="llama-3.1-8b-instant"): # Default Groq model (Highest Daily Limit)
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        self.model_name = model
        # Secondary Groq selection for maximum throughput/fallback
        self.groq_model_secondary = "llama-3.3-70b-versatile"

        # 1. Initialize Groq (Primary)
        if self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
        else:
            self.groq_client = None

        # 2. Initialize OpenRouter (Secondary/Tertiary)
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key
            )
        else:
            self.openrouter_client = None

    def generate_script(self, topic, category="General"):
        """Generates a video script. Hierarchy: Groq (Primary) -> Groq (Secondary) -> OpenRouter -> Ollama."""
        
        category_prompts = {
            "Bible": "You are a biblical scholar for maker Studio. Focus on historical accuracy and theological significance. Keep the script VERY SHORT (under 150 words).",
            "History": "You are a historian for maker Studio. Focus on pivotal figures and events. Keep the script VERY SHORT (under 150 words).",
            "News": "You are a news anchor for maker Studio. Focus on facts and concise delivery. Keep the script VERY SHORT (under 150 words).",
            "General": "You are a content creator for maker Studio. Create a concise video script. Keep the script VERY SHORT (under 150 words)."
        }

        system_prompt = category_prompts.get(category, category_prompts["General"])
        user_prompt = f"Topic: {topic}\nFormat: Hook, Main Content, CTA. STRICTLY LIMIT response to 150 words total."

        # 1. Try Groq (Primary & Secondary Failover)
        if self.groq_client:
            for current_model in [self.model_name, self.groq_model_secondary]:
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
                    print(f"ERROR: Groq model {current_model} failed: {e}.")
                    if current_model == self.groq_model_secondary:
                        print("Both Groq models failed. Falling back to OpenRouter.")

        # 2. Try OpenRouter (Secondary)
        if self.openrouter_client:
            try:
                # Use a free/cheap model on OpenRouter as fallback
                fallback_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001") 
                response = self.openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    extra_headers={
                        "HTTP-Referer": "https://maker.studio", # Optional, for including your app on openrouter.ai rankings.
                        "X-Title": "Maker Studio", # Optional. Shows in rankings on openrouter.ai.
                    }
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"ERROR: OpenRouter failed: {e}. Falling back to Ollama.")

        # 3. Try Ollama (Fallback)
        try:
            ollama_response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False},
                timeout=30
            )
            if ollama_response.status_code == 200:
                return ollama_response.json().get("response", "")
        except Exception as e:
            print(f"ERROR: Ollama fallback failed: {e}.")

        return "Error: Could not generate script with any provider."

    def generate_hooks(self, script):
        """Generates 3 viral hooks. Hierarchy: Groq (Primary) -> Groq (Secondary) -> OpenRouter -> Ollama."""
        prompt = f"Based on this script, generate 3 viral hooks for a TikTok/Shorts video. Make them high-impact.\n\nScript: {script}"
        
        # 1. Try Groq (Primary & Secondary Failover)
        if self.groq_client:
            for current_model in [self.model_name, self.groq_model_secondary]:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=current_model,
                    )
                    return chat_completion.choices[0].message.content
                except Exception as e:
                    print(f"ERROR: Groq model {current_model} failed for hooks: {e}.")

        # 2. Try OpenRouter (Secondary)
        if self.openrouter_client:
            try:
                fallback_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
                response = self.openrouter_client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except: pass

        # 3. Try Ollama (Fallback)
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": prompt, "stream": False},
                timeout=15
            )
            return response.json().get("response", "")
        except:
            return "1. Viral Hook 1\n2. Viral Hook 2\n3. Viral Hook 3 (Fallback)"

if __name__ == "__main__":
    gen = ScriptGenerator()
    script = gen.generate_script("The invention of the Printing Press", "History")
    print("--- GENERATED SCRIPT ---")
    print(script)
    print("\n--- GENERATED HOOKS ---")
    print(gen.generate_hooks(script))

