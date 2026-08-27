import ResultCard from "./ResultCard.jsx";

function Avatar({ initials, color, isBot }) {
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded ${color} text-sm font-bold text-white`}
    >
      {isBot ? <BotGlyph /> : initials}
    </div>
  );
}

function BotGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M12 2a1 1 0 0 1 1 1v1.5h3A3.5 3.5 0 0 1 19.5 8v6a3.5 3.5 0 0 1-3.5 3.5h-1.2l-2.02 2.24a1 1 0 0 1-1.56 0L9.2 17.5H8A3.5 3.5 0 0 1 4.5 14V8A3.5 3.5 0 0 1 8 4.5h3V3a1 1 0 0 1 1-1Zm-2.25 7a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5Zm4.5 0a1.25 1.25 0 1 0 0 2.5 1.25 1.25 0 0 0 0-2.5Z" />
    </svg>
  );
}

export default function SlackMessage({ message }) {
  const isBot = message.role === "bot";

  return (
    <div className="group flex gap-3 px-5 py-2 hover:bg-[#f8f8f8]">
      <Avatar
        initials={message.initials}
        color={isBot ? "bg-[#1264A3]" : message.color}
        isBot={isBot}
      />

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[15px] font-black text-slate-900">
            {isBot ? "CPaaS Bot" : message.author}
          </span>
          {isBot && (
            <span className="rounded bg-slate-200 px-1 py-px text-[10px] font-bold uppercase tracking-wide text-slate-600">
              App
            </span>
          )}
          <span className="text-xs text-slate-500">{message.time}</span>
          {message.contextUsed && (
            <span
              className="rounded bg-violet-50 px-1.5 py-px text-[10px] font-medium text-violet-700 ring-1 ring-inset ring-violet-200"
              title="This answer was resolved using the previous message in the thread"
            >
              resolved from context
            </span>
          )}
        </div>

        <div className="mt-0.5">
          {message.pending ? (
            <TypingIndicator />
          ) : isBot ? (
            <ResultCard
              answer={message.text}
              records={message.records}
              entityType={message.entityType}
              action={message.action}
              source={message.source}
            />
          ) : (
            <p className="whitespace-pre-wrap text-[15px] text-slate-800">
              {message.text}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1.5" aria-label="CPaaS Bot is typing">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}
