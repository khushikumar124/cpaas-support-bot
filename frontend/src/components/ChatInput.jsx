import { useRef, useEffect } from "react";

/**
 * Message composer fixed at the bottom of the chat area.
 */
export default function ChatInput({ value, onChange, onSubmit, disabled }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSubmit(e);
    }
  };

  return (
    <div className="border-t border-slate-200 bg-white px-4 py-4 sm:px-6">
      <form
        onSubmit={onSubmit}
        className="mx-auto flex max-w-3xl items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm focus-within:border-teal-500 focus-within:ring-2 focus-within:ring-teal-500/20"
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about numbers, gateways, tickets, customers..."
          disabled={disabled}
          className="max-h-40 min-h-[24px] flex-1 resize-none bg-transparent text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none disabled:opacity-50"
          aria-label="Message input"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-700 text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="Send message"
        >
          <SendIcon />
        </button>
      </form>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-slate-400">
        CPaaS support assistant · Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}

function SendIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
      className="h-5 w-5"
    >
      <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
    </svg>
  );
}
