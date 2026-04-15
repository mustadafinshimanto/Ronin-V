"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Ollama LLM Wrapper                ║
║         Direct interface to dolphin-llama3:8b             ║
╚══════════════════════════════════════════════════════════╝
"""

import sys
import ollama
from typing import Generator
from core.prompts import RONIN_SYSTEM_PROMPT


class RoninLLM:
    """
    Simple Ollama wrapper for Ronin-V.
    Single model, streaming responses, conversation history management.
    """

    def __init__(self, config: dict):
        """
        Initialize the LLM wrapper.
        
        Args:
            config: Parsed config.yaml as dict
        """
        self.model_name = config["model"]["name"]
        self.base_model = config["model"]["base"]
        self.ctx_length = config["model"].get("ctx_length", 8192)
        self.temperature = config["model"].get("temperature", 0.7)
        self.top_p = config["model"].get("top_p", 0.9)

        ollama_host = config["ollama"].get("host", "http://localhost:11434")
        self.timeout = config["ollama"].get("timeout", 120)
        self.keep_alive = config["ollama"].get("keep_alive", "10m")

        # Initialize Ollama client
        self.client = ollama.Client(host=ollama_host, timeout=self.timeout)

    def check_connection(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            self.client.list()
            return True
        except Exception:
            return False

    def check_model(self) -> bool:
        """Check if the required model is available locally."""
        try:
            models = self.client.list()
            model_names = []
            # Handle both dict and object response formats
            model_list = models.get("models", []) if isinstance(models, dict) else getattr(models, "models", [])
            for m in model_list:
                name = m.get("name", "") if isinstance(m, dict) else getattr(m, "model", "")
                model_names.append(name)
            
            # Check for both custom name and base model
            for name in model_names:
                if self.model_name in name or self.base_model in name:
                    return True
            return False
        except Exception:
            return False

    def get_compute_info(self) -> dict:
        """Query Ollama for loaded models and their hardware acceleration status."""
        try:
            # client.ps() returns currently running models
            running = self.client.ps()
            models = running.get("models", []) if isinstance(running, dict) else getattr(running, "models", [])
            
            for m in models:
                # Normalizing model name check
                name = m.get("name", "") if isinstance(m, dict) else getattr(m, "model", "")
                if self.model_name in name or self.base_model in name:
                    # Look for compute/vram in details
                    details = m.get("details", {}) if isinstance(m, dict) else getattr(m, "details", {})
                    # In newer Ollama, 'processor' or checking vram_usage is better
                    vram = m.get("vram_usage", 0) if isinstance(m, dict) else getattr(m, "size_vram", 0)
                    
                    if vram > 0 or "gpu" in str(details).lower():
                        return {"name": name, "gpu": True, "type": "GPU Accelerator"}
                    else:
                        return {"name": name, "gpu": False, "type": "CPU Fallback"}
            
            # If not in 'ps', it's not currently loaded - check list() for the name
            return {"name": self.model_name, "gpu": False, "type": "Ollama Standby"}
        except Exception:
            return {"name": self.model_name, "gpu": False, "type": "DISCONNECTED"}

    def pull_model(self, progress_callback=None) -> bool:
        """
        Pull the base model from Ollama registry.
        
        Args:
            progress_callback: Optional callable(status_str) for progress updates
        """
        try:
            stream = self.client.pull(self.base_model, stream=True)
            for chunk in stream:
                if progress_callback:
                    status = chunk.get("status", "") if isinstance(chunk, dict) else getattr(chunk, "status", "")
                    progress_callback(status)
            return True
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {e}")
            return False

    def chat(self, messages: list[dict], stream: bool = True) -> Generator[str, None, None] | str:
        """
        Send a chat request to the model.
        """
        options = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.ctx_length,
        }

        try:
            if stream:
                return self._stream_chat(messages, options)
            else:
                response = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    options=options,
                    keep_alive=self.keep_alive,
                )
                content = ""
                if isinstance(response, dict):
                    content = response.get("message", {}).get("content", "")
                else:
                    content = getattr(getattr(response, "message", None), "content", "")
                return content
        except ollama.ResponseError as e:
            if e.status_code == 404:
                # Model not found by custom name — try base model
                self.model_name = self.base_model
                if stream:
                    return self._stream_chat(messages, options)
                else:
                    response = self.client.chat(
                        model=self.model_name,
                        messages=messages,
                        options=options,
                        keep_alive=self.keep_alive,
                    )
                    content = ""
                    if isinstance(response, dict):
                        content = response.get("message", {}).get("content", "")
                    else:
                        content = getattr(getattr(response, "message", None), "content", "")
                    return content
            raise e

    def _stream_chat(self, messages: list[dict], options: dict) -> Generator[str, None, None]:
        """Internal streaming chat implementation."""
        try:
            stream = self.client.chat(
                model=self.model_name,
                messages=messages,
                options=options,
                stream=True,
                keep_alive=self.keep_alive,
            )
            for chunk in stream:
                if not chunk: continue
                
                if isinstance(chunk, dict):
                    # Standard dict response
                    content = chunk.get("message", {}).get("content", "")
                elif hasattr(chunk, "message"):
                    # Object response (newer SDK versions)
                    content = getattr(chunk.message, "content", "")
                else:
                    # Raw string fallback
                    content = str(chunk)

                if content:
                    yield content
        except Exception as e:
            yield f"\n[error]Neural Stream Error: {str(e)}[/error]"

    def one_shot(self, prompt: str) -> str:
        """
        Quick one-shot query without conversation history.
        Non-streaming, returns full response.
        
        Args:
            prompt: The user prompt
            
        Returns:
            Full response string
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, stream=False)
