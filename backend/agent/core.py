"""Core conversation engine."""

import uuid
from openai import OpenAI

from config import OPENAI_API_KEY, CHAT_MODEL, SYSTEM_PROMPT
from agent.memory import MemoryStore
from agent.reflection import run_reflection


client = OpenAI(api_key=OPENAI_API_KEY)


class BrainAgent:
    def __init__(self):
        self.memory = MemoryStore()
        self.sessions: dict[str, list[dict]] = {}

    def chat(self, message: str, session_id: str | None = None) -> dict:
        if not session_id:
            session_id = str(uuid.uuid4())

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # Store user message
        self.memory.store_message("user", message, session_id)
        self.sessions[session_id].append({"role": "user", "content": message})

        # Retrieve relevant context
        context = self._build_context(message)

        # Build messages for API call
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            api_messages.append({
                "role": "system",
                "content": f"Relevant knowledge from memory:\n{context}",
            })

        # Include recent conversation history
        recent = self.sessions[session_id][-20:]  # Last 20 messages
        api_messages.extend(recent)

        # Call OpenAI
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=api_messages,
            temperature=0.7,
            max_tokens=4000,
        )

        assistant_message = resp.choices[0].message.content

        # Store assistant response
        self.memory.store_message("assistant", assistant_message, session_id)
        self.sessions[session_id].append({"role": "assistant", "content": assistant_message})

        # Trigger reflection every 6 messages (3 exchanges)
        if len(self.sessions[session_id]) % 6 == 0:
            run_reflection(self.memory, self.sessions[session_id][-6:])

        return {
            "response": assistant_message,
            "session_id": session_id,
        }

    def _build_context(self, query: str) -> str:
        """Retrieve relevant facts and past conversations."""
        parts = []

        # Search facts
        facts = self.memory.search_facts(query, top_k=5)
        if facts:
            fact_texts = [f"- {f['content']}" for f in facts if f["score"] > 0.5]
            if fact_texts:
                parts.append("Known facts:\n" + "\n".join(fact_texts))

        # Search past conversations for relevant context
        conv_results = self.memory.search_conversations(query, top_k=3)
        if conv_results:
            relevant = [r for r in conv_results if r["score"] > 0.6]
            if relevant:
                conv_texts = [f"- [{r['metadata']['role']}]: {r['content'][:200]}" for r in relevant]
                parts.append("Related past discussions:\n" + "\n".join(conv_texts))

        return "\n\n".join(parts)

    def end_session(self, session_id: str):
        """End a session and run final reflection."""
        if session_id in self.sessions:
            messages = self.sessions[session_id]
            if len(messages) >= 4:
                run_reflection(self.memory, messages)
            del self.sessions[session_id]

    def get_facts(self, limit: int = 50) -> list[dict]:
        return self.memory.get_all_facts(limit=limit)

    def get_sessions(self) -> list[str]:
        return list(self.sessions.keys())
