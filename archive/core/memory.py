"""
╔══════════════════════════════════════════════════════════╗
║              RONIN-V — Memory Engine                     ║
║         ChromaDB vector store + SQLite session log        ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions


class RoninMemory:
    """
    Dual-layer memory system:
    - Short-term: sliding window of recent messages (in RAM)
    - Long-term: ChromaDB vector database for semantic recall
    - Session log: SQLite for persistent history with timestamps
    """

    def __init__(self, config: dict):
        """
        Initialize memory systems.
        
        Args:
            config: Parsed config.yaml as dict
        """
        mem_config = config.get("memory", {})
        data_dir = config.get("ronin", {}).get("data_dir", "./data")

        # Short-term memory (conversation sliding window)
        self.short_term: list[dict] = []
        self.window_size = mem_config.get("short_term_window", 20)

        # ChromaDB for long-term vector memory
        chroma_path = mem_config.get("chroma_path", os.path.join(data_dir, "chroma_db"))
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Use Ollama for embeddings if configured, otherwise default to local MiniLM
        embed_model = mem_config.get("embedding_model", "nomic-embed-text")
        ollama_host = config.get("ollama", {}).get("host", "http://localhost:11434")
        
        embedding_function = embedding_functions.OllamaEmbeddingFunction(
            model_name=embed_model,
            url=f"{ollama_host}/api/embeddings"
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="ronin_memory",
            embedding_function=embedding_function,
            metadata={"description": "Ronin-V long-term conversation memory"}
        )

        # SQLite session log
        session_db_path = mem_config.get("session_db", os.path.join(data_dir, "sessions", "ronin.db"))
        Path(session_db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(session_db_path)
        self._init_db()

        # RAG retrieval count
        self.max_context_docs = mem_config.get("max_context_docs", 5)

    def _init_db(self):
        """Create session tables if they don't exist."""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON messages(session_id)
        """)
        self.db.commit()

    # ─── Short-Term Memory ───

    def add_message(self, role: str, content: str, session_id: str, metadata: dict | None = None):
        """
        Add a message to both short-term and long-term memory.
        """
        # Type Safety: Ensure content is a string (prevents generator leaks)
        if not isinstance(content, str):
            if hasattr(content, "__iter__"):
                content = "".join([str(c) for c in content])
            else:
                content = str(content)

        message = {"role": role, "content": content}
        
        # Add to short-term sliding window
        self.short_term.append(message)
        if len(self.short_term) > self.window_size:
            self.short_term = self.short_term[-self.window_size:]

        # Log to SQLite
        self._log_to_db(session_id, role, content, metadata)

        # Add to ChromaDB for semantic search (skip very short messages)
        if len(content.strip()) > 20:
            self._add_to_vector_store(role, content, session_id)

    def get_context(self) -> list[dict]:
        """
        Get the current conversation context (short-term window).
        
        Returns:
            List of message dicts for the LLM
        """
        return list(self.short_term)

    def clear_short_term(self):
        """Clear the short-term conversation window."""
        self.short_term.clear()

    # ─── Long-Term Memory (ChromaDB) ───

    def _add_to_vector_store(self, role: str, content: str, session_id: str):
        """Embed and store a message in ChromaDB."""
        try:
            # Create a unique ID from content hash + timestamp
            doc_id = hashlib.md5(
                f"{content}{datetime.now().isoformat()}".encode()
            ).hexdigest()

            self.collection.add(
                documents=[f"[{role}] {content}"],
                metadatas=[{
                    "role": role,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }],
                ids=[doc_id]
            )
        except Exception:
            # Non-critical — don't crash if embedding fails
            pass

    def recall(self, query: str, n: int | None = None) -> list[dict]:
        """
        Semantic search over long-term memory.
        
        Args:
            query: Search query text
            n: Number of results (defaults to max_context_docs)
            
        Returns:
            List of relevant past interactions with metadata
        """
        if n is None:
            n = self.max_context_docs

        try:
            # Check if collection has any documents
            if self.collection.count() == 0:
                return []

            results = self.collection.query(
                query_texts=[query],
                n_results=min(n, self.collection.count())
            )

            memories = []
            if results and results.get("documents"):
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    distance = results["distances"][0][i] if results.get("distances") else None
                    memories.append({
                        "content": doc,
                        "timestamp": meta.get("timestamp", "unknown"),
                        "session_id": meta.get("session_id", "unknown"),
                        "relevance": 1 - (distance or 0)  # Convert distance to similarity
                    })

            return memories
        except Exception:
            return []

    # ─── Session Log (SQLite) ───

    def _log_to_db(self, session_id: str, role: str, content: str, metadata: dict | None = None):
        """Write a message to the session log."""
        try:
            self.db.execute(
                "INSERT INTO messages (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    datetime.now().isoformat(),
                    role,
                    content,
                    json.dumps(metadata) if metadata else None,
                )
            )
            self.db.commit()
        except Exception:
            pass

    def start_session(self, session_id: str):
        """Record the start of a new session."""
        try:
            self.db.execute(
                "INSERT INTO sessions (session_id, started_at) VALUES (?, ?)",
                (session_id, datetime.now().isoformat())
            )
            self.db.commit()
        except Exception:
            pass

    def end_session(self, session_id: str):
        """Record the end of a session."""
        try:
            self.db.execute(
                "UPDATE sessions SET ended_at = ? WHERE session_id = ?",
                (datetime.now().isoformat(), session_id)
            )
            self.db.commit()
        except Exception:
            pass

    def get_session_history(self, session_id: str) -> list[dict]:
        """
        Retrieve all messages from a specific session.
        
        Args:
            session_id: Session to retrieve
            
        Returns:
            List of message dicts ordered by timestamp
        """
        try:
            cursor = self.db.execute(
                "SELECT timestamp, role, content, metadata FROM messages WHERE session_id = ? ORDER BY timestamp",
                (session_id,)
            )
            return [
                {
                    "timestamp": row[0],
                    "role": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3]) if row[3] else None,
                }
                for row in cursor.fetchall()
            ]
        except Exception:
            return []

    def get_recent_sessions(self, limit: int = 10) -> list[dict]:
        """Get a list of recent sessions."""
        try:
            cursor = self.db.execute(
                "SELECT session_id, started_at, ended_at FROM sessions ORDER BY started_at DESC LIMIT ?",
                (limit,)
            )
            return [
                {
                    "session_id": row[0],
                    "started_at": row[1],
                    "ended_at": row[2],
                }
                for row in cursor.fetchall()
            ]
        except Exception:
            return []

    def close(self):
        """Clean up database connections."""
        try:
            self.db.close()
        except Exception:
            pass
