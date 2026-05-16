# Bio-Brain

AI assistant for biology research. Context-aware, learns from conversations, self-improves over time.

## Architecture

```
bio-brain/
├── backend/          # Python AI agent
│   ├── agent/
│   │   ├── core.py       # Conversation engine (OpenAI API)
│   │   ├── memory.py     # Hybrid retrieval (vector + FTS)
│   │   ├── reflection.py # Post-conversation fact extraction
│   │   └── tools.py      # PubMed, biology tools
│   ├── knowledge/
│   │   ├── ingest.py     # PDF/paper ingestion
│   │   └── store.py      # ChromaDB + SQLite interface
│   ├── api.py            # FastAPI server
│   ├── config.py         # Settings + API keys
│   ├── main.py           # Entry point
│   └── requirements.txt
├── webapp/           # React frontend (Peel-style, green theme)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── lib/
│   ├── tailwind.config.ts
│   └── package.json
└── CLAUDE.md
```

## Tech Stack

### Backend
- Python 3.11+
- OpenAI API (GPT-4o) for LLM + embeddings
- ChromaDB for vector store (local, file-based)
- SQLite for conversation history + structured memory
- FastAPI for HTTP API
- Key: stored in backend/.env (gitignored)

### Frontend
- React 18 + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- TanStack Query for data fetching
- React Router
- Design: Peel-style editorial (serif headings, mono labels, cards) with green/bio color scheme

## Design System (Green/Bio theme)
- Primary accent: emerald/teal green
- Background: warm paper with slight sage tint
- Typography: Instrument Serif (display), Geist (body), Geist Mono (labels)
- Same editorial feel as Peel but biology-focused

## Key Decisions
- Raw OpenAI calls, no LangChain (transparent, debuggable)
- Hybrid search: vector similarity + SQLite FTS5 for keyword precision
- Every conversation triggers a reflection step that extracts facts
- Memory is tiered: mentioned once = stub, mentioned multiple times = enriched
- Backend serves API, frontend is separate SPA
- Chat-first interface with knowledge sidebar

## Commands
- Backend: `cd backend && pip install -r requirements.txt && python main.py`
- Frontend: `cd webapp && bun install && bun run dev`
- Backend runs on port 8000, frontend on port 5173

## Environment
- OpenAI API key in backend/.env as OPENAI_API_KEY
- Never commit .env files
