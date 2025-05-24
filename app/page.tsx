"use client";
import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessage {
  role: "user" | "system";
  text: string;
  timestamp: string;
}

const AI_AVATAR = (
  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-lg border-2 border-blue-300">
    <span>🤖</span>
  </div>
);
const USER_AVATAR = (
  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-700 to-blue-400 flex items-center justify-center text-white font-bold text-xl shadow-lg border-2 border-blue-300">
    <span>🧑</span>
  </div>
);

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([{
    role: "system",
    text: "Hi! I'm Gemini, your ISV AI assistant. Ask me to find or enrich software vendors for you!",
    timestamp: formatTime(new Date()),
  }]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const now = new Date();
    const userMsg: ChatMessage = { role: "user", text: input, timestamp: formatTime(now) };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    try {
      // Prepare history for backend (excluding system prompt)
      const history = newMessages.slice(1).map((msg) => ({ role: msg.role, text: msg.text }));
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ history }),
      });
      const data = await res.json();
      setMessages((msgs) => [
        ...msgs,
        { role: "system", text: data.response || data.error || "[No response from Gemini]", timestamp: formatTime(new Date()) },
      ]);
    } catch (err) {
      setMessages((msgs) => [
        ...msgs,
        { role: "system", text: "Error connecting to Gemini backend.", timestamp: formatTime(new Date()) },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full flex flex-col justify-end items-center overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 -z-10 bg-gradient-to-br from-[#0f172a] via-[#1e293b] to-[#312e81] animate-gradient-move" />
      {/* Chat area */}
      <div className="w-full flex-1 flex flex-col justify-end pb-40 px-0">
        <div className="overflow-y-auto flex-1 mb-4 p-6 mt-10 w-full">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`my-3 flex items-end gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "system" && AI_AVATAR}
              <div
                className={`relative group rounded-2xl px-6 py-4 max-w-3xl w-full whitespace-pre-wrap text-base shadow-xl transition-all duration-200 flex flex-col bg-opacity-90 border backdrop-blur-md animate-fade-in ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-blue-600 to-blue-400 text-white ml-auto items-end border-blue-400 hover:shadow-blue-400/40"
                    : "bg-white/10 text-blue-100 border border-blue-900 mr-auto items-start hover:shadow-purple-400/40"
                }`}
                style={{ wordBreak: 'break-word' }}
              >
                {msg.role === "system" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      strong: ({ node, ...props }) => <strong className="font-bold text-blue-200" {...props} />,
                      em: ({ node, ...props }) => <em className="italic text-blue-300" {...props} />,
                      u: ({ node, ...props }) => <u className="underline decoration-blue-400" {...props} />,
                      li: ({ node, ...props }) => <li className="ml-4 list-disc text-blue-100" {...props} />,
                      ul: ({ node, ...props }) => <ul className="pl-4 mb-2" {...props} />,
                      ol: ({ node, ...props }) => <ol className="pl-4 mb-2 list-decimal" {...props} />,
                      a: ({ node, ...props }) => <a className="text-blue-300 underline" target="_blank" rel="noopener noreferrer" {...props} />,
                      code: ({ node, ...props }) => <code className="bg-blue-950 text-blue-200 px-1 py-0.5 rounded" {...props} />,
                      blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-blue-400 pl-4 italic text-blue-200 my-2" {...props} />,
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                ) : (
                  <span className="transition-opacity duration-300 group-hover:opacity-80">{msg.text}</span>
                )}
                <span className="text-xs text-gray-500 mt-1 self-end opacity-60 group-hover:opacity-100">{msg.timestamp}</span>
              </div>
              {msg.role === "user" && USER_AVATAR}
            </div>
          ))}
          {loading && (
            <div className="my-3 flex justify-start items-center gap-2">
              {AI_AVATAR}
              <div className="rounded-2xl px-6 py-4 max-w-3xl w-full whitespace-pre-wrap text-base shadow-xl bg-white/10 text-blue-100 border border-blue-900 flex items-center animate-fade-in">
                <span className="animate-pulse">Gemini is typing...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      {/* Input bar */}
      <form
        onSubmit={handleSend}
        className="fixed bottom-0 left-0 w-full flex justify-center z-20"
      >
        <div className="w-full flex items-center gap-2 px-4 pb-8">
          <div className="flex-1 flex items-center bg-white/10 backdrop-blur-md rounded-2xl shadow-lg border border-blue-900 px-4 py-3">
            <input
              type="text"
              className="flex-1 bg-transparent text-white placeholder-gray-400 focus:outline-none text-lg"
              placeholder="Type your ISV search or question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              autoFocus
            />
          </div>
          <button
            type="submit"
            className="px-7 py-3 bg-gradient-to-br from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-2xl text-white font-bold shadow-lg transition disabled:opacity-60 text-lg"
            disabled={loading || !input.trim()}
          >
            {loading ? (
              <span className="animate-pulse">...</span>
            ) : (
              "Send"
            )}
          </button>
        </div>
      </form>
      {/* Animations */}
      <style jsx global>{`
        @keyframes gradient-move {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .animate-gradient-move {
          background-size: 200% 200%;
          animation: gradient-move 12s ease-in-out infinite;
        }
        .animate-fade-in {
          animation: fadeIn 0.7s;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: none; }
        }
      `}</style>
    </div>
  );
}