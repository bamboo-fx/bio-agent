"""Post-conversation reflection: extracts facts and learns from interactions."""

import json
from openai import OpenAI

from config import OPENAI_API_KEY, CHAT_MODEL


client = OpenAI(api_key=OPENAI_API_KEY)

EXTRACTION_PROMPT = """You are a knowledge extraction system. Analyze this conversation and extract:

1. **Facts**: Specific biological facts, research findings, or domain knowledge mentioned
2. **User preferences**: Communication style, topics of interest, expertise areas
3. **Corrections**: Anything the user corrected or clarified

Return JSON with this structure:
{
  "facts": [
    {"content": "...", "category": "molecular_biology|genetics|ecology|biochemistry|evolution|methods|general", "confidence": 0.5-1.0}
  ],
  "preferences": [
    {"key": "...", "value": "..."}
  ],
  "corrections": [
    {"wrong": "...", "right": "..."}
  ]
}

Only extract genuinely useful, specific information. Skip pleasantries and generic statements.
If there's nothing worth extracting, return empty arrays.

Conversation:
"""


def extract_knowledge(messages: list[dict]) -> dict:
    """Run reflection on a conversation to extract learnable knowledge."""
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )

    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000,
        )
        result = json.loads(resp.choices[0].message.content)
        return {
            "facts": result.get("facts", []),
            "preferences": result.get("preferences", []),
            "corrections": result.get("corrections", []),
        }
    except Exception as e:
        print(f"Reflection error: {e}")
        return {"facts": [], "preferences": [], "corrections": []}


def run_reflection(memory_store, messages: list[dict]):
    """Extract knowledge from messages and store it."""
    if len(messages) < 4:  # Need at least 2 exchanges to be worth reflecting
        return

    knowledge = extract_knowledge(messages)

    for fact in knowledge["facts"]:
        memory_store.store_fact(
            content=fact["content"],
            category=fact.get("category", "general"),
            source="conversation",
        )

    for pref in knowledge["preferences"]:
        memory_store.set_user_pref(pref["key"], pref["value"])

    # Handle corrections by storing the correct version as high-confidence facts
    for correction in knowledge["corrections"]:
        memory_store.store_fact(
            content=f"CORRECTION: {correction['right']} (previously incorrectly stated as: {correction['wrong']})",
            category="correction",
            source="user_correction",
        )

    return knowledge
