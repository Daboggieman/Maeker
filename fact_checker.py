import os
from llm_router import LLMRouter  # pyre-ignore

class FactChecker:
    def __init__(self, model="llama-3.3-70b-versatile"):
        self.router = LLMRouter(primary_groq_model=model)

    def verify_script(self, script, category="History"):
        """Cross-references script content using available LLMs. Hierarchy: Groq -> OpenRouter -> Ollama."""
        
        system_prompt = f"You are an expert fact-checker specializing in {category}. Your job is to find any inaccuracies in the provided script and provide corrections."
        user_prompt = f"Please review the following script for accuracy:\n\n{script}"

        response = self.router.route_request(system_prompt, user_prompt, response_format="text")
        if response:
            return response

        return "Error: Could not verify script with any provider."

if __name__ == "__main__":
    checker = FactChecker()
