import os
import time
import requests
from groq import Groq, RateLimitError, APIStatusError, APIError # type: ignore 
from openai import OpenAI, RateLimitError as OpenAIRateLimitError, APIStatusError as OpenAIAPIStatusError, APIError as OpenAIAPIError # type: ignore
from dotenv import load_dotenv

load_dotenv()

class LLMRouter:
    """
    Centralized Gateway for handling large language model API requests.
    Manages robust fallback hierarchies, handles rate limit backoffs (429),
    credit issues (402), and service outages (503/500).
    """

    def __init__(self, primary_groq_model="llama-3.1-8b-instant", secondary_groq_model="llama-3.3-70b-versatile"):
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        self.primary_groq = primary_groq_model
        self.secondary_groq = secondary_groq_model
        
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None
        
        if self.openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key
            )
        else:
            self.openrouter_client = None

    def route_request(self, system_prompt: str, user_prompt: str, response_format: str = "text") -> str | None:
        """
        Executes a robust multi-provider fallback.
        Groq (Primary Model) »»» Groq (Secondary Model) »»» OpenRouter (Secondary Provider) »»» Ollama (Local Fallback)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        kwargs = {}
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        # Groq
        if self.groq_client:
            for current_model in [self.primary_groq, self.secondary_groq]:
                try:
                    return self._execute_groq(messages, current_model, **kwargs)
                except Exception as e:
                    print(f"WARN: Groq model {current_model} exhausted/failed: {e}")

        # OpenRouter
        if self.openrouter_client:
            try:
                return self._execute_openrouter(messages, self.openrouter_model, **kwargs)
            except Exception as e:
                print(f"WARN: OpenRouter {self.openrouter_model} exhausted/failed: {e}")

        # Ollama
        try:
            return self._execute_ollama(system_prompt, user_prompt, response_format)
        except Exception as e:
            print(f"WARN: Ollama fallback failed: {e}")

        print("ERROR: All API providers failed (Groq, OpenRouter, Ollama) on route_request.")
        return None

    def _execute_groq(self, messages: list, model: str, **kwargs) -> str:
        """Executes a Groq chat completion with smart exponential backoff."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=model,
                    **kwargs
                )
                return response.choices[0].message.content
            except RateLimitError as e:
                # HTTP 429
                wait_time = min(15 * (attempt + 1), 35)
                print(f"WARN: [GROQ 429] Rate Limit on {model}. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            except APIStatusError as e:
                status = e.status_code
                if status in [502, 503]:
                    # Server overload, wait and retry logic
                    wait_time = min(10 * (attempt + 1), 30)
                    print(f"WARN: [GROQ {status}] Server Overloaded on {model}. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                elif status in [400, 401, 403, 404]: # Bad Request, Unauthorized, Auth Failed
                    print(f"ERROR: [GROQ {status}] Authentication or Malformed Request. Instantly failing over.")
                    raise e
                else:
                    raise e
            except Exception as e:
                raise e

        # Out of retries
        raise Exception("Max retries exceeded for Groq.")

    def _execute_openrouter(self, messages: list, model: str, **kwargs) -> str:
        """Executes an OpenRouter chat completion with smart fallback and backoff."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Work on a copy to avoid mutating the shared messages list across retries
                msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
                if "response_format" in kwargs and kwargs["response_format"].get("type") == "json_object":
                    if "JSON" not in msgs[0]["content"]:
                        msgs[0]["content"] += "\nReturn strictly as JSON without markdown blocks."
                        
                response = self.openrouter_client.chat.completions.create(
                    messages=msgs,
                    model=model,
                    extra_headers={
                        "HTTP-Referer": "https://maker.studio",
                        "X-Title": "Maker Studio",
                    }
                )
                content = response.choices[0].message.content
                
                # Cleanup markdown blocks if json requested
                if "response_format" in kwargs:
                    content = content.replace("```json", "").replace("```", "").strip()
                return content
                
            except OpenAIRateLimitError as e:
                wait_time = min(15 * (attempt + 1), 35) 
                print(f"WARN: [OpenRouter 429] Rate Limit on {model}. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            except OpenAIAPIStatusError as e:
                status = e.status_code 
                if status == 402:
                    print("CRITICAL: [OpenRouter 402] Out of Credits! Instantly skipping provider.")
                    raise e
                elif status in [502, 503]:
                    wait_time = min(10 * (attempt + 1), 30)
                    print(f"WARN: [OpenRouter {status}] Overload. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                elif status in [400, 401, 403, 404]:
                    print(f"ERROR: [OpenRouter {status}] Malformed or Auth Issue. Instantly failing over.")
                    raise e
                else:
                    raise e
            except Exception as e:
                raise e

        raise Exception("Max retries exceeded for OpenRouter.")

    def _execute_ollama(self, system_prompt: str, user_prompt: str, response_format: str) -> str:
        """Executes a local Ollama generation."""
        payload = {
            "model": "llama3.2", 
            "prompt": f"{system_prompt}\n\n{user_prompt}", 
            "stream": False
        }
        if response_format == "json":
            payload["format"] = "json"

        response = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=45)
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama returned HTTP {response.status_code}")

    def get_active_providers(self) -> list[str]:
        """Returns a list of successfully configured provider names."""
        providers = []
        if self.groq_key: providers.append("Groq")
        if self.openrouter_key: providers.append("OpenRouter")
        
        # Quick check for Ollama availability
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=1)
            if resp.status_code == 200:
                providers.append("Ollama (Local)")
        except: pass
        
        return providers
