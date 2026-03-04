/**
 * NeufinChatbot — floating AI Concierge for the public landing page.
 *
 * Uses a plain <button> FAB (no Framer Motion on the trigger) and CSS
 * transitions for the chat window to guarantee click reliability.
 *
 * Answers common FAQ questions locally; falls back to POST /api/v1/concierge/chat.
 */
import { useState, useRef, useEffect } from 'react';
import { Sparkles, X, Send, Bot, User, ChevronDown } from 'lucide-react';
import axios from 'axios';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

/* ── Local FAQ lookup (covers all ExpandedFAQ content) ─────────────────────── */
const FAQ_KB: Array<{ keywords: string[]; answer: string }> = [
  {
    keywords: ['neural twin', 'what is neufin', 'how does it work', 'digital mirror'],
    answer:
      'A Neural Twin is a digital mirror of your investment strategy — without the cognitive biases. It analyses your historical trades, spots bias-driven decisions (loss aversion, confirmation bias, FOMO), and simulates what a perfectly rational version of you would have done. It stress-tests decisions against 10,000 scenarios before making a recommendation.',
  },
  {
    keywords: ['7-day trial', 'free trial', '7 day', 'how long trial'],
    answer:
      'Neufin offers a comprehensive 7-day free trial with full access to the Neural Twin AI, real-time bias alerts, the AI Behavioural Coach, and the Emotional Breaker kill switch — no credit card required for early-access registrants. After 7 days you can upgrade to Pro.',
  },
  {
    keywords: ['cognitive bias', 'biases', 'detect bias', 'how many biases', '47'],
    answer:
      'Neufin tracks 47 distinct cognitive biases including loss aversion, disposition effect, confirmation bias, and herding behaviour. Each bias is quantified with an exact dollar impact so you know precisely what emotional decisions are costing you annually.',
  },
  {
    keywords: ['pricing', 'price', 'cost', 'how much', 'plan', 'subscription'],
    answer:
      'Neufin offers three plans: Individual ($49/mo), Professional Trader ($149/mo), and Enterprise (custom). All include a 7-day free trial. Early-bird waitlist members receive 50% off for the first 3 months — up to $223 in savings.',
  },
  {
    keywords: ['early bird', 'waitlist', 'discount', 'join', '50%'],
    answer:
      'Early-bird waitlist members get 50% off all plans for the first 3 months, priority onboarding with a dedicated specialist, lifetime "Early Adopter" badge, and guaranteed price lock for 12 months. Limited to the first 500 registrants.',
  },
  {
    keywords: ['security', 'safe', 'protect', 'encrypt', 'privacy', 'data'],
    answer:
      'Neufin uses SOC 2 Type II certified infrastructure, 256-bit AES encryption at rest, TLS 1.3 in transit, and zero-knowledge architecture — we never store your brokerage passwords. Authentication uses read-only OAuth tokens via Plaid that you can revoke anytime.',
  },
  {
    keywords: ['execute trade', 'trade on my behalf', 'automated', 'auto trade'],
    answer:
      'No — Neufin is a decision-intelligence platform, not a trading bot. We provide analysis and signals; you maintain complete control. Our Plaid integration is read-only by default. Any trade execution requires your explicit two-factor approval.',
  },
  {
    keywords: ['cancel', 'cancellation', 'delete data', 'data portability'],
    answer:
      'On cancellation you enter a 30-day grace period with read-only access to export all your data (CSV, PDF, JSON). After that you can request permanent deletion (GDPR "Right to be Forgotten") within 7 business days, or archive for up to 12 months.',
  },
  {
    keywords: ['brokerage', 'robinhood', 'schwab', 'fidelity', 'td ameritrade', 'integration', 'connect'],
    answer:
      'Neufin integrates with 12,000+ financial institutions via Plaid — including Robinhood, Schwab, Fidelity, TD Ameritrade, Interactive Brokers, Webull, and more. Manual CSV upload and cryptocurrency via Coinbase/Kraken are also supported.',
  },
  {
    keywords: ['mobile', 'app', 'ios', 'android', 'iphone'],
    answer:
      'Yes — native iOS (15+) and Android (10+) apps are available on the App Store and Google Play. Features include real-time push alerts for high-confidence signals, bias alerts, sentiment heatmap, and one-tap portfolio sync via biometrics.',
  },
  {
    keywords: ['return', 'alpha', 'performance', 'result', 'how much money'],
    answer:
      'In our beta (500+ users, 6 months) average Alpha improvement was +3.2% annualised with a +0.34 Sharpe ratio improvement. 68% of users who followed debiasing recommendations outperformed their previous 12-month baseline. Past performance does not guarantee future results.',
  },
  {
    keywords: ['accuracy', 'signal', 'how accurate'],
    answer:
      'Neufin\'s sentiment signals achieve 73% directional accuracy over rolling 6-month periods. Alpha predictions have 89% correlation with actual outcomes. Bias interventions show an 82% success rate when acted on within the suggested timeframe.',
  },
  {
    keywords: ['international', 'uk', 'europe', 'canada', 'global', 'non-us'],
    answer:
      'Neufin\'s primary focus is US markets, but you can manually enter positions from any global exchange. UK and Canadian broker integrations are planned for Q2 2025, with full multi-currency support in Q3 2025.',
  },
  {
    keywords: ['how long', 'when see results', 'timeline', 'results time'],
    answer:
      'You get an instant Alpha Score analysis on Day 1. Measurable behavioural change typically starts in Month 1-3 (+1.8% average Alpha in first quarter). By Month 3-6 your Neural Twin is fully personalised, accelerating to +3.2% annualised improvement.',
  },
];

function localLookup(input: string): string | null {
  const lower = input.toLowerCase();
  for (const entry of FAQ_KB) {
    if (entry.keywords.some((kw) => lower.includes(kw))) {
      return entry.answer;
    }
  }
  return null;
}

/* ── API call ───────────────────────────────────────────────────────────────── */
const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

async function askConcierge(message: string): Promise<string> {
  const { data } = await axios.post<{ reply: string }>(
    `${API_BASE}/concierge/chat`,
    { message },
    { timeout: 12000 },
  );
  return data.reply;
}

/* ── Initial greeting ───────────────────────────────────────────────────────── */
const INITIAL: Message = {
  id: 'init',
  role: 'assistant',
  content:
    "Hi! I'm the Neufin AI Concierge. Ask me anything about Neural Twin technology, pricing, security, or how to get started.",
};

const QUICK_STARTS = [
  'How does the 7-day trial work?',
  'What is a Neural Twin?',
  'What biases does Neufin detect?',
  'How is my data protected?',
];

/* ── Component ──────────────────────────────────────────────────────────────── */
export function NeufinChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([INITIAL]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  /* Scroll to bottom + focus input when opened or new message added */
  useEffect(() => {
    if (!open) return;
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      if (messages.length === 1) inputRef.current?.focus();
    }, 80);
  }, [open, messages.length]);

  const send = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { id: `u-${Date.now()}`, role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    /* 1. Check local FAQ first (instant, no network) */
    const localAnswer = localLookup(trimmed);
    if (localAnswer) {
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', content: localAnswer },
      ]);
      setLoading(false);
      return;
    }

    /* 2. Fall back to backend */
    try {
      const reply = await askConcierge(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', content: reply },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content:
            "I'm temporarily unavailable. For immediate help email us at info@neufin.ai — or try one of the quick-start questions below.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* ── Chat window — outer shell controls visibility; inner panel owns background ── */}
      <div
        className="fixed right-6 z-[9999] w-[360px] max-w-[calc(100vw-1.5rem)] rounded-2xl"
        style={{
          bottom: '5.5rem',
          height: 480,
          opacity: open ? 1 : 0,
          transform: open ? 'translateY(0) scale(1)' : 'translateY(12px) scale(0.97)',
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 200ms ease, transform 200ms ease',
        }}
        aria-hidden={!open}
      >
        {/* Inner solid panel — neufin-panel here so opacity:1!important doesn't conflict with the outer toggle */}
        <div
          className="neufin-panel flex flex-col h-full w-full rounded-2xl shadow-2xl shadow-black/60"
          style={{
            backgroundColor: '#0D1117',
            opacity: 1,
            backdropFilter: 'none',
            border: '1px solid #30363D',
          }}
        >

        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3 border-b border-white/5 shrink-0 rounded-t-2xl"
          style={{ backgroundColor: '#0D1117' }}
        >
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-purple-700/30 border border-purple-600/40 flex items-center justify-center">
              <Bot className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white leading-none">Neufin AI Concierge</p>
              <p className="text-[10px] text-purple-400 mt-0.5">Neural Twin Technology</p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
            aria-label="Minimise chat"
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
                    ? 'bg-purple-700/30 border border-purple-600/30'
                    : 'bg-white/10'
                }`}
              >
                {msg.role === 'assistant' ? (
                  <Bot className="w-3 h-3 text-purple-400" />
                ) : (
                  <User className="w-3 h-3 text-gray-300" />
                )}
              </div>
              <div
                className={`max-w-[82%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
                  msg.role === 'assistant'
                    ? 'text-gray-200 rounded-tl-sm'
                    : 'text-gray-100 rounded-tr-sm'
                }`}
                style={{
                  backgroundColor:
                    msg.role === 'assistant' ? '#151A23' : '#3B1F6E',
                }}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {/* Loading dots */}
          {loading && (
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-purple-700/30 border border-purple-600/30 flex items-center justify-center shrink-0">
                <Bot className="w-3 h-3 text-purple-400" />
              </div>
              <div
                className="px-3 py-2 rounded-xl rounded-tl-sm flex gap-1 items-center"
                style={{ backgroundColor: '#151A23' }}
              >
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-1.5 h-1.5 rounded-full animate-bounce"
                    style={{ backgroundColor: 'rgba(124,58,237,0.6)', animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Quick-start chips — only shown on the initial message */}
        {messages.length === 1 && (
          <div className="px-4 pb-2 flex flex-wrap gap-1.5 shrink-0">
            {QUICK_STARTS.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="text-[10px] px-2.5 py-1 rounded-full border transition-colors"
                style={{
                  backgroundColor: 'rgba(124,58,237,0.1)',
                  borderColor: 'rgba(124,58,237,0.25)',
                  color: '#a78bfa',
                }}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form
          onSubmit={(e) => { e.preventDefault(); send(input); }}
          className="flex items-center gap-2 px-4 py-3 border-t border-white/5 shrink-0 rounded-b-2xl"
          style={{ backgroundColor: '#0D1117' }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about Neural Twin…"
            disabled={loading}
            className="flex-1 rounded-lg px-3 py-2 text-xs text-gray-200 placeholder-gray-600 outline-none border transition-colors"
            style={{
              backgroundColor: '#151A23',
              borderColor: 'rgba(255,255,255,0.1)',
            }}
            onFocus={(e) =>
              (e.currentTarget.style.borderColor = 'rgba(124,58,237,0.5)')
            }
            onBlur={(e) =>
              (e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)')
            }
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ backgroundColor: '#7C3AED' }}
          >
            <Send className="w-3.5 h-3.5 text-white" />
          </button>
        </form>
        </div>{/* end neufin-panel inner div */}
      </div>{/* end outer visibility wrapper */}

      {/* ── FAB — plain <button>, no Framer Motion on the trigger ── */}
      <div className="fixed bottom-6 right-6 z-[9999]">
        {/* Pulse ring (CSS only, pointer-events-none) */}
        {!open && (
          <span
            className="absolute inset-0 rounded-full animate-ping pointer-events-none"
            style={{ backgroundColor: 'rgba(124,58,237,0.35)' }}
          />
        )}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="relative w-14 h-14 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-105 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400"
          style={{
            backgroundColor: '#7C3AED',
            boxShadow: '0 4px 24px rgba(124,58,237,0.45)',
          }}
          aria-label={open ? 'Close AI chat' : 'Open Neufin AI chat'}
          aria-expanded={open}
        >
          {open ? (
            <X className="w-6 h-6 text-white" />
          ) : (
            <Sparkles className="w-6 h-6 text-white" />
          )}
        </button>
      </div>
    </>
  );
}
