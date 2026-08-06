import { useEffect, useRef } from "react";
import Message from "./Message.jsx";

/**
 * Scrollable message list for the active conversation.
 */
export default function ChatWindow({ messages, isLoading, onSelectExample }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-6 sm:px-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {isEmpty && <WelcomePanel onSelectExample={onSelectExample} />}

          {messages.map((msg) => (
            <Message
              key={msg.id}
              role={msg.role}
              content={msg.content}
            />
          ))}

          {isLoading && (
            <Message role="assistant" content="" isLoading />
          )}

          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}

function WelcomePanel({ onSelectExample }) {
  const examples = [
    "What is the status of 9152001212?",
    "Who owns gateway 470?",
    "Show all active numbers",
    "Show all open tickets",
    "Show all Vodafone numbers",
    "waht is the staus of 9152001212",
  ];

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-700 text-2xl font-bold text-white shadow-lg">
        C
      </div>
      <h2 className="text-2xl font-semibold text-slate-800">
        CPaaS Support Assistant
      </h2>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        Ask natural language questions about gateways, VMNs, customers, and
        tickets. Follow-up questions like &ldquo;who owns it?&rdquo; work too.
      </p>
      <p className="mt-3 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
        Demo build — all data below is fictional
      </p>
      <div className="mt-8 grid w-full max-w-lg gap-2 text-left sm:grid-cols-2">
        {examples.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onSelectExample?.(text)}
            className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm text-slate-600 transition hover:border-teal-300 hover:bg-white hover:text-slate-900"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
