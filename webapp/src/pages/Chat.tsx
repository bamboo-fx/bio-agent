import { useState, useRef, useEffect } from "react";
import { Send, Upload, Brain, Dna, Leaf } from "lucide-react";
import { sendMessage, getFacts, uploadDocument } from "@/lib/api";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [facts, setFacts] = useState<Array<{ id: number; content: string; category: string; mentions: number }>>([]);
  const [showKnowledge, setShowKnowledge] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await sendMessage(userMsg, sessionId);
      setSessionId(res.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await uploadDocument(file);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Ingested **${result.file}**: processed ${result.chunks_processed} chunks, extracted ${result.facts_extracted} facts.`,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Failed to upload document." },
      ]);
    }
    e.target.value = "";
  };

  const loadFacts = async () => {
    try {
      const res = await getFacts();
      setFacts(res.facts);
    } catch {}
    setShowKnowledge(!showKnowledge);
  };

  return (
    <div className="flex h-screen bg-paper">
      {/* Sidebar - Knowledge Panel */}
      {showKnowledge && (
        <aside className="hidden w-80 flex-col border-r border-border bg-card md:flex">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-display text-xl text-ink">Knowledge Base</h2>
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft">
              {facts.length} facts stored
            </p>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {facts.map((fact) => (
              <div key={fact.id} className="mb-3 rounded-lg border border-border/70 bg-secondary/30 p-3">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center rounded-full bg-bio/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-bio-deep">
                    {fact.category}
                  </span>
                  {fact.mentions > 1 && (
                    <span className="font-mono text-[10px] text-ink-soft">
                      {fact.mentions}x
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm leading-relaxed text-ink">{fact.content}</p>
              </div>
            ))}
            {facts.length === 0 && (
              <p className="text-center text-sm text-ink-soft">
                No facts yet. Start chatting to build knowledge.
              </p>
            )}
          </div>
        </aside>
      )}

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-border bg-card/80 px-5 py-3 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-bio/10">
              <Dna className="h-5 w-5 text-bio-deep" strokeWidth={1.6} />
            </div>
            <div>
              <h1 className="font-display text-xl leading-tight text-ink">Bio-Brain</h1>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ink-soft">
                AI Research Assistant
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadFacts}
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                showKnowledge
                  ? "border-bio bg-bio/10 text-bio-deep"
                  : "border-border text-ink-soft hover:border-bio/50 hover:text-ink"
              }`}
            >
              <Brain className="h-3.5 w-3.5" />
              Knowledge
            </button>
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-ink-soft transition-colors hover:border-bio/50 hover:text-ink"
            >
              <Upload className="h-3.5 w-3.5" />
              Ingest
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.md"
              className="hidden"
              onChange={handleUpload}
            />
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="mx-auto max-w-3xl px-4 py-6">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`mb-6 flex gap-3 ${msg.role === "user" ? "justify-end" : ""}`}
                >
                  {msg.role === "assistant" && (
                    <div className="mt-1 flex h-7 w-7 flex-none items-center justify-center rounded-md bg-bio/10">
                      <Leaf className="h-4 w-4 text-bio-deep" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-ink text-background"
                        : "border border-border/70 bg-card text-ink"
                    }`}
                  >
                    <div className="prose prose-sm max-w-none [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="mb-6 flex gap-3">
                  <div className="mt-1 flex h-7 w-7 flex-none items-center justify-center rounded-md bg-bio/10">
                    <Leaf className="h-4 w-4 text-bio-deep" />
                  </div>
                  <div className="rounded-2xl border border-border/70 bg-card px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span className="h-2 w-2 animate-pulse-soft rounded-full bg-bio" />
                      <span className="h-2 w-2 animate-pulse-soft rounded-full bg-bio [animation-delay:0.3s]" />
                      <span className="h-2 w-2 animate-pulse-soft rounded-full bg-bio [animation-delay:0.6s]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border bg-card/80 px-4 py-4 backdrop-blur-sm">
          <div className="mx-auto flex max-w-3xl items-end gap-3">
            <div className="flex-1 rounded-xl border border-border bg-background focus-within:border-bio/50 focus-within:ring-1 focus-within:ring-bio/20">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about biology, research, or anything..."
                rows={1}
                className="w-full resize-none bg-transparent px-4 py-3 text-sm text-ink placeholder:text-ink-soft/60 focus:outline-none"
                style={{ minHeight: "44px", maxHeight: "160px" }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "44px";
                  target.style.height = target.scrollHeight + "px";
                }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-bio text-white transition-colors hover:bg-bio-deep disabled:opacity-40 disabled:hover:bg-bio"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-bio/10">
        <Dna className="h-8 w-8 text-bio-deep" strokeWidth={1.4} />
      </div>
      <h2 className="font-display mt-6 text-3xl text-ink">Bio-Brain</h2>
      <p className="mt-2 max-w-md text-center text-sm leading-relaxed text-ink-soft">
        Your AI research assistant. Ask questions, discuss ideas, upload papers.
        I learn from our conversations and get better over time.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { icon: Dna, label: "Explain CRISPR-Cas9 off-target effects" },
          { icon: Leaf, label: "How does quorum sensing work?" },
          { icon: Brain, label: "Review my hypothesis on gene regulation" },
        ].map((s) => (
          <div
            key={s.label}
            className="flex items-center gap-2.5 rounded-lg border border-border/70 bg-card px-4 py-3 text-xs text-ink-soft transition-colors hover:border-bio/30 hover:text-ink"
          >
            <s.icon className="h-4 w-4 flex-none text-bio" />
            <span>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
