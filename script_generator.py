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
            "Bible": "You are a biblical scholar for Maker Studio. Write a highly detailed, extremely educational, and highly entertaining narrative focused on historical accuracy. You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags like 'Hook:' or 'Main Content:'. Output must be pure spoken English.",
            "History": "You are a historian for Maker Studio. Write a highly detailed, extremely educational, and highly entertaining narrative focusing on pivotal figures and events. You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags. Output must be pure spoken English.",
            "News": "You are a news anchor for Maker Studio. Write a highly detailed, extremely entertaining narrative focusing on facts. You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags. Output must be pure spoken English.",
            "General": "You are a master storyteller for Maker Studio. Write a highly detailed, extremely entertaining, and very educative script. You MUST use simple, everyday conversational 5th-grade English that anyone can easily understand. Avoid sophisticated or complex vocabulary. DO NOT USE structural tags like 'Hook:', brackets, or bullet points. It must read like a natural, flowing story."
        }

        system_prompt = category_prompts.get(category, category_prompts["General"])
        user_prompt = f"Topic: {topic}\nWrite a fluid, deeply detailed, and very long script. Use highly accessible 5th-grade English. Do NOT use any headings, brackets, or bullet points. It must read entirely as continuous, engaging spoken narration."

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
                    print(f"WARN: Groq model {current_model} failed: {e}. Trying fallback...")

        # 2. Try OpenRouter (Secondary Failover)
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
                print(f"WARN: OpenRouter fallback failed: {e}. Trying Ollama...")

        # 3. Try Ollama (Ultimate Offline Fallback)
        try:
            ollama_response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False},
                timeout=30
            )
            if ollama_response.status_code == 200:
                return ollama_response.json().get("response", "")
        except Exception as e:
            print(f"ERROR: Ollama fallback failed: {e}")

        return "Error: Could not generate script from any provider."

    def generate_scenes(self, script):
        """Breaks a script into scenes with image prompts. Hierarchy: Groq -> OpenRouter -> Ollama."""
        import json
        system_prompt = "You are an expert video director. Break the script into logical, sequential scenes."
        user_prompt = f"""
Analyze the following script and break it down into scenes.
Return ONLY a JSON object with a single key "scenes" containing an array of scene objects. Do not use markdown blocks.

Each scene object must have:
1. "narration": The EXACT chunk of text from the script to be spoken. Do not summarize, skip, or change the text. Every single word of the script must be included across the narrations.
2. "image_prompt": A highly detailed visual prompt for an AI image generator describing the scene (cinematic, highly detailed, photorealistic).

Example format:
{{
  "scenes": [
    {{
      "narration": "In the heart of the ancient city, long before the empires of dust...",
      "image_prompt": "Cinematic wide shot of an ancient bustling city, golden hour, highly detailed."
    }}
  ]
}}

Script:
{script}
"""
        
        # 1. Try Groq (Primary & Secondary)
        if self.groq_client:
            for current_model in [self.model_name, self.groq_model_secondary]:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model=current_model,
                        response_format={"type": "json_object"}
                    )
                    return json.loads(chat_completion.choices[0].message.content).get("scenes", [])
                except Exception as e:
                    print(f"ERROR: Groq model {current_model} failed for scenes: {e}.")

        # 2. Try OpenRouter (Secondary)
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
                text = response.choices[0].message.content
                # Very basic cleanup in case of markdown
                text = text.replace("```json", "").replace("```", "").strip()
                return json.loads(text).get("scenes", [])
            except: pass

        # 3. Try Ollama (Fallback)
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": "llama3.2", "prompt": f"{system_prompt}\n\n{user_prompt}", "stream": False, "format": "json"},
                timeout=30
            )
            if response.status_code == 200:
                text = response.json().get("response", "{}")
                return json.loads(text).get("scenes", [])
        except Exception as e:
            print(f"ERROR: Ollama fallback failed for scenes: {e}.")

        # Ultimate fallback: Make the whole script one scene
        return [{"narration": script, "image_prompt": "Cinematic high-quality visual", "tone": "informative"}]

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

