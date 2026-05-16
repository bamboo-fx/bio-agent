"""Hybrid memory system: ChromaDB (vector) + SQLite (FTS + structured)."""

import sqlite3
import json
import time
from pathlib import Path
from openai import OpenAI

import chromadb
from chromadb.config import Settings

from config import OPENAI_API_KEY, EMBEDDING_MODEL, DB_PATH, CHROMA_PATH


client = OpenAI(api_key=OPENAI_API_KEY)


def get_embedding(text: str) -> list[float]:
    resp = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return resp.data[0].embedding


class MemoryStore:
    def __init__(self):
        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        self.db = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT
            );

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                source TEXT,
                confidence REAL DEFAULT 0.8,
                mentions INTEGER DEFAULT 1,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                content, category, source
            );

            CREATE TABLE IF NOT EXISTS user_prefs (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            );
        """)
        self.db.commit()

    def _init_chroma(self):
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.chroma = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        self.facts_collection = self.chroma.get_or_create_collection(
            name="facts",
            metadata={"hnsw:space": "cosine"},
        )
        self.conversations_collection = self.chroma.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"},
        )

    def store_message(self, role: str, content: str, session_id: str):
        now = time.time()
        self.db.execute(
            "INSERT INTO conversations (timestamp, role, content, session_id) VALUES (?, ?, ?, ?)",
            (now, role, content, session_id),
        )
        self.db.commit()

        # Store in vector DB for semantic search over past conversations
        doc_id = f"{session_id}_{role}_{int(now * 1000)}"
        self.conversations_collection.add(
            ids=[doc_id],
            documents=[content],
            embeddings=[get_embedding(content)],
            metadatas=[{"role": role, "session_id": session_id, "timestamp": now}],
        )

    def store_fact(self, content: str, category: str = "general", source: str = "conversation"):
        now = time.time()

        # Check if similar fact exists (dedup)
        existing = self.search_facts(content, top_k=1)
        if existing and existing[0]["score"] > 0.92:
            # Update mention count instead of adding duplicate
            fact_id = existing[0]["id"]
            self.db.execute(
                "UPDATE facts SET mentions = mentions + 1, updated_at = ? WHERE id = ?",
                (now, fact_id),
            )
            self.db.commit()
            return fact_id

        cursor = self.db.execute(
            "INSERT INTO facts (content, category, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (content, category, source, now, now),
        )
        fact_id = cursor.lastrowid
        self.db.commit()

        # FTS index
        self.db.execute(
            "INSERT INTO facts_fts (rowid, content, category, source) VALUES (?, ?, ?, ?)",
            (fact_id, content, category, source),
        )
        self.db.commit()

        # Vector index
        self.facts_collection.add(
            ids=[str(fact_id)],
            documents=[content],
            embeddings=[get_embedding(content)],
            metadatas=[{"category": category, "source": source, "fact_id": fact_id}],
        )

        return fact_id

    def search_facts(self, query: str, top_k: int = 5) -> list[dict]:
        """Hybrid search: vector similarity + FTS."""
        results = []

        # Vector search
        try:
            vector_results = self.facts_collection.query(
                query_embeddings=[get_embedding(query)],
                n_results=min(top_k, self.facts_collection.count() or 1),
            )
            if vector_results["ids"] and vector_results["ids"][0]:
                for i, doc_id in enumerate(vector_results["ids"][0]):
                    results.append({
                        "id": int(doc_id) if doc_id.isdigit() else doc_id,
                        "content": vector_results["documents"][0][i],
                        "score": 1 - (vector_results["distances"][0][i] if vector_results["distances"] else 0),
                        "source": "vector",
                    })
        except Exception:
            pass

        # FTS search
        try:
            fts_rows = self.db.execute(
                "SELECT rowid, content, category, source FROM facts_fts WHERE facts_fts MATCH ? LIMIT ?",
                (query, top_k),
            ).fetchall()
            for row in fts_rows:
                # Avoid duplicates
                if not any(r["id"] == row[0] for r in results):
                    results.append({
                        "id": row[0],
                        "content": row[1],
                        "score": 0.7,  # FTS doesn't give a similarity score
                        "source": "fts",
                    })
        except Exception:
            pass

        # Sort by score, return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_conversations(self, query: str, top_k: int = 5) -> list[dict]:
        """Search past conversations by semantic similarity."""
        try:
            count = self.conversations_collection.count()
            if count == 0:
                return []
            vector_results = self.conversations_collection.query(
                query_embeddings=[get_embedding(query)],
                n_results=min(top_k, count),
            )
            results = []
            if vector_results["ids"] and vector_results["ids"][0]:
                for i, doc_id in enumerate(vector_results["ids"][0]):
                    results.append({
                        "content": vector_results["documents"][0][i],
                        "metadata": vector_results["metadatas"][0][i],
                        "score": 1 - (vector_results["distances"][0][i] if vector_results["distances"] else 0),
                    })
            return results
        except Exception:
            return []

    def get_recent_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        rows = self.db.execute(
            "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in reversed(rows)]

    def get_all_facts(self, limit: int = 100) -> list[dict]:
        rows = self.db.execute(
            "SELECT id, content, category, source, confidence, mentions, created_at FROM facts ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"id": r[0], "content": r[1], "category": r[2], "source": r[3],
             "confidence": r[4], "mentions": r[5], "created_at": r[6]}
            for r in rows
        ]

    def get_user_pref(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM user_prefs WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_user_pref(self, key: str, value):
        now = time.time()
        self.db.execute(
            "INSERT OR REPLACE INTO user_prefs (key, value, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), now),
        )
        self.db.commit()
