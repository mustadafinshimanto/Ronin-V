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

        # System message — always first in conversation
        import platform
        os_name = platform.system()
        os_release = platform.release()
        
        self.system_message = {
            "role": "system",
            "content": RONIN_SYSTEM_PROMPT.format(os=os_name, os_release=os_release)
        }

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
        
        Args:
            messages: List of message dicts [{"role": "user/assistant", "content": "..."}]
            stream: Whether to stream the response token by token
            
        Yields:
            Response content chunks (if streaming)
            
        Returns:
            Full response string (if not streaming)
        """
        # Prepend system message
        full_messages = [self.system_message] + messages

        options = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "num_ctx": self.ctx_length,
        }

        try:
            if stream:
                return self._stream_chat(full_messages, options)
            else:
                response = self.client.chat(
                    model=self.model_name,
                    messages=full_messages,
                    options=options,
                    keep_alive=self.keep_alive,
                )
                content = ""
                if isinstance(response, dict):
                    content = response.get("message", {}).get("content", "")
                else:
                    content = getattr(getattr(response, "message", None), "content", "")
                return content
        except ollama.ResponseError:
            # Model not found by custom name — try base model
            self.model_name = self.base_model
            if stream:
                return self._stream_chat(full_messages, options)
            else:
                response = self.client.chat(
                    model=self.model_name,
                    messages=full_messages,
                    options=options,
                    keep_alive=self.keep_alive,
                )
                content = ""
                if isinstance(response, dict):
                    content = response.get("message", {}).get("content", "")
                else:
                    content = getattr(getattr(response, "message", None), "content", "")
                return content

    def _stream_chat(self, messages: list[dict], options: dict) -> Generator[str, None, None]:
        """Internal streaming chat implementation."""
        stream = self.client.chat(
            model=self.model_name,
            messages=messages,
            options=options,
            stream=True,
            keep_alive=self.keep_alive,
        )
        for chunk in stream:
            if isinstance(chunk, dict):
                content = chunk.get("message", {}).get("content", "")
            else:
                content = getattr(getattr(chunk, "message", None), "content", "")
            if content:
                yield content

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
