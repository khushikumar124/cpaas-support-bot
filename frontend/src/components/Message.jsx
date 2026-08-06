/**
 * Single chat message bubble (user or assistant).
 */
export default function Message({ role, content, isLoading = false }) {
  const isUser = role === "user";

  return (
    <div
      className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`flex max-w-[85%] gap-3 sm:max-w-[75%] ${
          isUser ? "flex-row-reverse" : "flex-row"
        }`}
      >
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-xs font-semibold ${
            isUser
              ? "bg-teal-700 text-white"
              : "bg-slate-200 text-slate-700"
          }`}
          aria-hidden
        >
          {isUser ? "You" : "AI"}
        </div>

        <div
          className={`rounded-2xl px-4 py-3 text-[15px] leading-relaxed shadow-sm ${
            isUser
              ? "rounded-tr-md bg-teal-700 text-white"
              : "rounded-tl-md border border-slate-200 bg-white text-slate-800"
          }`}
        >
          {isLoading ? (
            <LoadingDots />
          ) : (
            <div className="whitespace-pre-wrap break-words">{content}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1" aria-label="Assistant is typing">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-slate-400 animate-pulse-dot"
          style={{ animationDelay: `${i * 0.2}s` }}
        />
      ))}
    </div>
  );
}
