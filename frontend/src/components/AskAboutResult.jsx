import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, Send, Loader2 } from "lucide-react";
import { askAboutResult } from "../api";

const INTRO_PROMPT =
  "In 2-3 sentences, explain why you likely predicted this emotion for my " +
  "voice based on the scores. End by inviting me to ask anything else or " +
  "letting me know you're here to help.";

export default function AskAboutResult({ result }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const [introLoading, setIntroLoading] = useState(true);
  const [error, setError] = useState(null);

  // Runs once on mount; introLoading/error already start as true/null.
  useEffect(() => {
    let cancelled = false;

    askAboutResult(INTRO_PROMPT, result)
      .then(({ answer }) => {
        if (!cancelled) setMessages([{ role: "assistant", content: answer }]);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || "Could not reach the AI assistant.");
      })
      .finally(() => {
        if (!cancelled) setIntroLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const busy = sending || introLoading;

  async function handleSubmit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    setSending(true);
    setError(null);

    try {
      const { answer } = await askAboutResult(q, result);
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch (e) {
      setError(e.message || "Could not reach the AI assistant.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
      <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide flex items-center gap-2">
        <MessageCircle size={16} /> Ask about this result
      </h3>

      {(messages.length > 0 || introLoading) && (
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl px-4 py-2 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-800 text-gray-200"
                  }`}
                >
                  {m.content}
                </div>
              </motion.div>
            ))}
            {introLoading && (
              <motion.div
                key="intro-loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="bg-gray-800 text-gray-500 rounded-xl px-4 py-2 text-sm flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin" /> Thinking…
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}

      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a follow-up question…"
          disabled={busy}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder:text-gray-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg transition-colors"
        >
          {sending ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Send size={16} />
          )}
        </button>
      </form>
    </div>
  );
}
