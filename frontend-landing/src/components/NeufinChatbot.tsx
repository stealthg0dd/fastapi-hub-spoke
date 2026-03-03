/**
 * NeufinChatbot — floating AI Concierge for the public landing page.
 *
 * • FAB with Sparkles icon in the bottom-right corner.
 * • Calls POST /api/v1/concierge/chat (exempt from Zero Trust auth).
 * • Quick-start buttons: "How does the 7-day trial work?" / "What is a Neural Twin?"
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sparkles, X, Send, Bot, User, ChevronDown } from 'lucide-react';
import axios from 'axios';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

const QUICK_STARTS = [
  { label: 'How does the 7-day trial work?', message: 'How does the 7-day trial work?' },
  { label: 'What is a Neural Twin?', message: 'What is a Neural Twin?' },
  { label: 'What biases does Neufin detect?', message: 'What cognitive biases does Neufin detect?' },
  { label: 'How is my data protected?', message: 'How is my financial data protected?' },
];

const INITIAL_MESSAGE: Message = {
  id: 'init',
  role: 'assistant',
  content:
    "Hello, I'm the Neufin AI Concierge. I can explain how our Neural Twin technology creates a digital mirror of your financial behavior to eliminate costly cognitive biases. What would you like to know?",
};

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

async function askConcierge(message: string): Promise<string> {
  const { data } = await axios.post<{ reply: string }>(`${API_BASE}/concierge/chat`, { message });
  return data.reply;
}

export function NeufinChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [open, messages]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const reply = await askConcierge(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'assistant', content: reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'I apologize — I seem to be temporarily unavailable. Please try again in a moment.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <>
      {/* Chat window */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="chat-window"
            initial={{ opacity: 0, scale: 0.92, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 16 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="fixed bottom-44 right-6 z-50 w-[360px] max-w-[calc(100vw-1.5rem)] bg-[#0D1117] border border-[#7C3AED]/30 rounded-2xl shadow-2xl shadow-black/60 flex flex-col overflow-hidden"
            style={{ height: 480 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-[#0D1117]">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ boxShadow: ['0 0 0px #7C3AED44', '0 0 12px #7C3AED88', '0 0 0px #7C3AED44'] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-7 h-7 rounded-full bg-[#7C3AED]/20 border border-[#7C3AED]/40 flex items-center justify-center"
                >
                  <Bot className="w-3.5 h-3.5 text-[#7C3AED]" />
                </motion.div>
                <div>
                  <p className="text-xs font-mono font-semibold text-white">Neufin AI Concierge</p>
                  <p className="text-[10px] font-mono text-[#7C3AED]">Neural Twin Technology</p>
                </div>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              >
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                      msg.role === 'assistant'
                        ? 'bg-[#7C3AED]/20 border border-[#7C3AED]/30'
                        : 'bg-white/10'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <Bot className="w-3 h-3 text-[#7C3AED]" />
                    ) : (
                      <User className="w-3 h-3 text-gray-300" />
                    )}
                  </div>
                  <div
                    className={`max-w-[82%] px-3 py-2 rounded-xl text-xs font-mono leading-relaxed ${
                      msg.role === 'assistant'
                        ? 'bg-[#151A23] text-gray-200 rounded-tl-sm'
                        : 'bg-[#7C3AED]/20 text-gray-100 rounded-tr-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}

              {/* Loading dots */}
              {loading && (
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-[#7C3AED]/20 border border-[#7C3AED]/30 flex items-center justify-center">
                    <Bot className="w-3 h-3 text-[#7C3AED]" />
                  </div>
                  <div className="bg-[#151A23] px-3 py-2 rounded-xl rounded-tl-sm flex gap-1">
                    {[0, 0.15, 0.3].map((delay) => (
                      <motion.div
                        key={delay}
                        className="w-1.5 h-1.5 bg-[#7C3AED]/60 rounded-full"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 0.9, repeat: Infinity, delay }}
                      />
                    ))}
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Quick-start chips — only shown when there's just the initial message */}
            {messages.length === 1 && (
              <div className="px-4 pb-2 flex flex-wrap gap-1.5">
                {QUICK_STARTS.map(({ label, message }) => (
                  <button
                    key={label}
                    onClick={() => send(message)}
                    className="text-[10px] font-mono px-2.5 py-1 rounded-full bg-[#7C3AED]/10 border border-[#7C3AED]/20 text-[#7C3AED] hover:bg-[#7C3AED]/20 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-2 px-4 py-3 border-t border-white/5"
            >
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about Neural Twin..."
                className="flex-1 bg-[#151A23] border border-white/10 rounded-lg px-3 py-2 text-xs font-mono text-gray-200 placeholder:text-gray-600 outline-none focus:border-[#7C3AED]/50 transition-colors"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={!input.trim() || loading}
                className="w-8 h-8 rounded-lg bg-[#7C3AED] hover:bg-[#6D28D9] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0"
              >
                <Send className="w-3.5 h-3.5 text-white" />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>

      {/* FAB — sits above the WhatsApp button */}
      <motion.button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-24 right-6 z-50 w-14 h-14 rounded-full bg-[#7C3AED] shadow-lg shadow-[#7C3AED]/40 flex items-center justify-center"
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        animate={open ? {} : { boxShadow: ['0 0 0px #7C3AED44', '0 0 20px #7C3AED88', '0 0 0px #7C3AED44'] }}
        transition={{ duration: 2.2, repeat: open ? 0 : Infinity }}
        aria-label={open ? 'Close AI chat' : 'Open AI chat'}
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.div key="close" initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <X className="w-6 h-6 text-white" />
            </motion.div>
          ) : (
            <motion.div key="open" initial={{ rotate: 90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: -90, opacity: 0 }} transition={{ duration: 0.15 }}>
              <Sparkles className="w-6 h-6 text-white" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </>
  );
}
