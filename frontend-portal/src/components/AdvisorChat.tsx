import { useState } from "react";
import apiClient from "../api/apiClient";
import type { ChatResponse } from "../api/types";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  piiCategories?: string[];
};

export function AdvisorChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      const { data } = await apiClient.post<ChatResponse>("/api/v1/chat", {
        prompt: trimmed,
      });

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.response,
        piiCategories: data.pii_detected ?? [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        id: `assistant-error-${Date.now()}`,
        role: "assistant",
        content: "Sorry, I could not reach the advisor. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col rounded-xl border border-[#1A1D23] bg-[#0D1117]">
      <div className="border-b border-[#1A1D23] px-4 py-2.5">
        <h2 className="text-xs font-mono text-white">AI Advisor</h2>
        <p className="text-[10px] font-mono text-gray-500">
          Ask about your trades, risk, and behavioral patterns.
        </p>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3 text-sm">
        {messages.length === 0 ? (
          <p className="text-xs font-mono text-gray-500">
            Start a conversation by asking, for example:{" "}
            <span className="text-gray-300">
              “What behavioral biases are most visible in my recent trades?”
            </span>
          </p>
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              className={`max-w-[90%] rounded-lg px-3 py-2 text-xs font-mono leading-relaxed ${
                m.role === "user"
                  ? "ml-auto bg-[#1F2933] text-white"
                  : "mr-auto bg-[#111827] text-gray-100"
              }`}
            >
              <div className="whitespace-pre-wrap">{m.content}</div>
              {m.role === "assistant" && m.piiCategories && m.piiCategories.length > 0 && (
                <div className="mt-2 border-t border-white/5 pt-1 text-[10px] text-gray-400">
                  Note: Certain sensitive data was redacted for your security.{" "}
                  <span className="opacity-70">
                    ({m.piiCategories.join(", ")})
                  </span>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="border-t border-[#1A1D23] px-3 py-2">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            className="min-h-[40px] flex-1 resize-none rounded-lg border border-[#1A1D23] bg-[#020617] px-3 py-2 text-xs font-mono text-white outline-none focus:border-[#00C087]"
            placeholder="Ask the advisor a question about your portfolio or trading behavior…"
          />
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
            className="mb-0.5 inline-flex h-9 items-center justify-center rounded-lg bg-[#00C087] px-3 text-xs font-mono text-black disabled:opacity-50"
          >
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

