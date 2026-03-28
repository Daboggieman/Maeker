import os
import re
from llm_router import LLMRouter  # pyre-ignore

class ScriptGenerator:
    def __init__(self, model="llama-3.1-8b-instant"):
        self.router = LLMRouter(primary_groq_model=model)

    def generate_script(self, topic, category="General"):
        """Generates a video script. Hierarchy: Groq (Primary) -> Groq (Secondary) -> OpenRouter -> Ollama."""
        
        category_prompts = {
            "Bible": "You are a biblical scholar and Preacher of the word of God for Maeker Studio. Write a highly detailed, extremely educational, inspirational, interesting, captivating, humourus, and highly entertaining narrative focused on historical accuracy and biblical accuracy (extreme bible accuracy). You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags like 'Hook:' or 'Main Content:'. Output must be pure spoken English.",
            "History": "You are a historian for Maeker Studio. Write a highly detailed, extremely educational, interesting, captivating, humourus, and highly entertaining narrative focusing on pivotal figures and events. You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags. Output must be pure spoken English.",
            "News": "You are a news anchor for Maker Studio. Write a highly detailed,  interesting, captivating, humourus, extremely entertaining narrative focusing on facts. You MUST use simple, everyday 5th-grade English. Do not use unusual, sophisticated, or complex words. DO NOT USE structural tags. Output must be pure spoken English.",
            "General": "You are a master storyteller for Maker Studio. Write a highly detailed, extremely entertaining, interesting, captivating, humourus, and very educative script. You MUST use simple, everyday conversational 5th-grade English that anyone can easily understand. Avoid sophisticated or complex vocabulary. DO NOT USE structural tags like 'Hook:', brackets, or bullet points. It must read like a natural, flowing story."
        }

        system_prompt = category_prompts.get(category, category_prompts["General"])
        user_prompt = f"Topic: {topic}\nWrite a fluid, deeply detailed, interesting, captivating, humourus and very long script. Use highly accessible 5th-grade English. Do NOT use any headings, brackets, or bullet points. It must read entirely as continuous, engaging spoken narration."

        response = self.router.route_request(system_prompt, user_prompt, response_format="text")
        if response:
            return response
            
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
CRITICAL TIMING RULE: A single scene should represent roughly 15 seconds of speaking time (maximum ~35-40 words). If a narrative block is longer than 40 words, you MUST break it entirely into multiple shorter scenes, each with its own image prompt.
2. "image_prompt": A highly detailed visual prompt for an AI image generator describing the scene. STRICT RULE: Ensure you only generate highly descriptive, detailed prompts. You MUST explicitly specify "no text, no typography, 8k, highly detailed, cinematic" at the end of every single image prompt to prevent AI artifacts.

Example format:
{{
  "scenes": [
    {{
      "narration": "In the heart of the ancient aztec city, long before the empires of dust...",
      "image_prompt": "Cinematic wide shot of an ancient bustling aztec city, golden hour, 8k resolution, highly detailed, photorealistic, no text, no typography."
    }}
  ]
}}

Script:
{script}
"""
        
        response = self.router.route_request(system_prompt, user_prompt, response_format="json")
        if response:
            try:
                return json.loads(response).get("scenes", [])
            except Exception as e:
                print(f"ERROR: Failed to parse JSON scenes: {e}")

        # Ultimate fallback: Make the whole script one scene
        return [{"narration": script, "image_prompt": "Cinematic high-quality visual", "tone": "informative"}]

    def generate_hooks(self, script):
        """Generates 3 viral hooks. Hierarchy: Groq (Primary) -> Groq (Secondary) -> OpenRouter -> Ollama."""
        prompt = f"Based on this script, generate 3 viral hooks for a TikTok/Shorts video. Make them high-impact.\n\nScript: {script}"
        
        response = self.router.route_request("You are a viral TikTok copywriter.", prompt, response_format="text")
        if response:
            return response
            
        return "1. Viral Hook 1\n2. Viral Hook 2\n3. Viral Hook 3 (Fallback)"

    def generate_upload_metadata(self, script: str, topic: str, category: str, hooks: str) -> dict:
        """
        Generates AI-crafted titles, descriptions, and tags for YouTube and TikTok.
        Returns a dict with keys: youtube_title, youtube_description, tiktok_title, tiktok_tags.
        """
        import json

        system_prompt = (
            "You are a world-class social media content strategist for Maeker Studios. "
            "You write viral, emotionally engaging copy that drives comments, shares, and views."
        )
        user_prompt = f"""
Create upload metadata for a video about: "{topic}" (Category: {category})

Hooks available: {hooks}

Return ONLY a JSON object with NO markdown, exactly this shape:
{{
  "youtube_title": "Max 100 chars. Punchy, curiosity-gap, SEO-optimised. No clickbait.",
  "youtube_description": "3-4 short paragraphs. First paragraph hooks instantly. Second gives context. Third compels viewers to DROP A COMMENT — ask a specific, thought-provoking question they can't resist answering. Fourth is a CTA (like, subscribe, share). End with 5-7 hashtags including #MaekerStudios. No timestamps.",
  "tiktok_title": "Max 150 chars. Hook-first, energetic, curiosity-driven caption for TikTok.",
  "tiktok_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
}}

Script excerpt (first 800 chars for context):
{script[:800]}  # type: ignore
"""
        response = self.router.route_request(system_prompt, user_prompt, response_format="json")
        if response:
            try:
                return json.loads(response)
            except Exception as e:
                print(f"ERROR: Failed to parse JSON upload metadata: {e}")

        # Fallback — sensible defaults so upload never crashes
        return {
            "youtube_title":       f"{topic} — Full Story | Maeker Studios",
            "youtube_description": (
                f"Dive into the fascinating story of {topic}.\n\n"
                f"What did YOU think about this? Drop your thoughts in the comments below — "
                f"we read every single one! 👇\n\n"
                f"👍 Like, 🔔 Subscribe, and share with someone who'd love this.\n\n"
                f"#{topic.replace(' ', '')} #{category} #History #MaekerStudios #Documentary"
            ),
            "tiktok_title":        f"You won't believe this story about {topic} 👀 #MaekerStudios",
            "tiktok_tags":         [topic.replace(" ", ""), category, "History", "MaekerStudios",
                                    "Documentary", "Storytelling", "DidYouKnow", "Viral",
                                    "FunFacts", "LearnOnTikTok"],
        }

if __name__ == "__main__":
    gen = ScriptGenerator()
    script = gen.generate_script("The invention of the Printing Press", "History")
    print("--- GENERATED SCRIPT ---")
    print(script)
    print("\n--- GENERATED HOOKS ---")
    print(gen.generate_hooks(script))


