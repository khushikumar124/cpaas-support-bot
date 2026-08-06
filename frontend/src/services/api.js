const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

// Only needed when the backend runs with DEMO_MODE=false and a BOT_API_KEY set.
// In the default demo build this is empty and no header is sent.
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function buildHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}

/**
 * Send a question to the CPaaS support bot API.
 *
 * @param {string} question       - The user's natural language question.
 * @param {string|null} conversationId - Stable chat session ID for context memory.
 *   Pass the active chat's ID so the backend can resolve follow-up questions
 *   like "What is its status?" using the previous turn's entity.
 *   Pass null for stateless one-off queries.
 * @returns {Promise<{ answer: string, context_used: boolean }>}
 */
export async function sendQuery(question, conversationId = null) {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify({
      question,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  return response.json();
}
