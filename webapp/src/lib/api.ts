const BASE = "";

export async function sendMessage(message: string, sessionId?: string) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json() as Promise<{ response: string; session_id: string }>;
}

export async function getFacts(limit = 50) {
  const res = await fetch(`${BASE}/api/facts?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch facts");
  return res.json() as Promise<{ facts: Array<{ id: number; content: string; category: string; mentions: number }> }>;
}

export async function uploadDocument(file: File) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/ingest`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}
