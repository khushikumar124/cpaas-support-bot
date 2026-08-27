import { useCallback, useEffect, useRef, useState } from "react";
import { sendQuery } from "../services/api.js";
import SlackMessage from "./SlackMessage.jsx";
import {
  CHANNELS,
  DIRECT_MESSAGES,
  OPENING_QUESTION,
  SEED_MESSAGES,
  SUGGESTIONS,
  WORKSPACE,
} from "./slackData.js";

const CONVERSATION_ID = "slack-demo-support-ops";

function now() {
  return new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function uid() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function userMessage(text) {
  return {
    id: uid(),
    role: "user",
    author: "You",
    initials: "YO",
    color: "bg-[#2BAC76]",
    time: now(),
    text,
  };
}

export default function SlackView({ onSwitchView }) {
  const [messages, setMessages] = useState(SEED_MESSAGES);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [activeChannel, setActiveChannel] = useState("support-ops");
  const bottomRef = useRef(null);
  const openedRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const ask = useCallback(async (question) => {
    const trimmed = question.trim();
    if (!trimmed) return;

    const pendingId = uid();
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      userMessage(trimmed),
      { id: pendingId, role: "bot", time: now(), pending: true },
    ]);

    try {
      const data = await sendQuery(trimmed, CONVERSATION_ID);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                pending: false,
                text: data.answer,
                records: data.records,
                entityType: data.entity_type,
                action: data.action,
                source: data.source,
                contextUsed: data.context_used,
              }
            : m
        )
      );
    } catch (error) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                pending: false,
                text: `Could not reach the backend: ${error.message}`,
              }
            : m
        )
      );
    } finally {
      setBusy(false);
    }
  }, []);

  // Open on a real exchange rather than a hardcoded one — this answer comes
  // from the live API on mount.
  useEffect(() => {
    if (openedRef.current) return;
    openedRef.current = true;
    ask(OPENING_QUESTION);
  }, [ask]);

  const submit = (event) => {
    event.preventDefault();
    if (busy) return;
    const question = input;
    setInput("");
    ask(question);
  };

  const channelName =
    CHANNELS.find((c) => c.id === activeChannel)?.name ?? activeChannel;

  return (
    <div className="flex h-screen overflow-hidden bg-white font-sans">
      <WorkspaceRail />
      <ChannelSidebar
        activeChannel={activeChannel}
        onSelect={setActiveChannel}
        onSwitchView={onSwitchView}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <ChannelHeader name={channelName} />

        <div className="flex-1 overflow-y-auto py-3">
          <ChannelIntro name={channelName} />
          {messages.map((message) => (
            <SlackMessage key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>

        <Composer
          value={input}
          onChange={setInput}
          onSubmit={submit}
          onSuggestion={(text) => ask(text)}
          disabled={busy}
          channelName={channelName}
        />
      </div>
    </div>
  );
}

function WorkspaceRail() {
  return (
    <div className="hidden w-[68px] shrink-0 flex-col items-center gap-4 bg-[#3F0E40] py-3 md:flex">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/90 text-lg font-black text-[#3F0E40]">
        C
      </div>
      <div className="h-px w-8 bg-white/20" />
      {["Home", "DMs", "Activity"].map((label, index) => (
        <button
          key={label}
          type="button"
          className={`flex h-10 w-10 flex-col items-center justify-center rounded-lg text-[10px] font-medium ${
            index === 0 ? "bg-white/20 text-white" : "text-white/70 hover:bg-white/10"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function ChannelSidebar({ activeChannel, onSelect, onSwitchView }) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col bg-[#3F0E40] text-white/80 lg:flex">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <span className="truncate text-[15px] font-black text-white">
          {WORKSPACE}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-3 text-[15px]">
        <SidebarSection title="Channels" />
        {CHANNELS.map((channel) => (
          <button
            key={channel.id}
            type="button"
            onClick={() => onSelect(channel.id)}
            className={`flex w-full items-center justify-between rounded px-2 py-1 text-left ${
              activeChannel === channel.id
                ? "bg-[#1164A3] text-white"
                : "hover:bg-white/10"
            }`}
          >
            <span className="truncate">
              <span className="mr-1 opacity-70">#</span>
              {channel.name}
            </span>
            {channel.unread > 0 && activeChannel !== channel.id && (
              <span className="ml-2 rounded-full bg-[#CD2553] px-1.5 text-xs font-bold text-white">
                {channel.unread}
              </span>
            )}
          </button>
        ))}

        <SidebarSection title="Direct messages" />
        {DIRECT_MESSAGES.map((dm) => (
          <div
            key={dm.id}
            className="flex items-center gap-2 rounded px-2 py-1 hover:bg-white/10"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                dm.presence === "active"
                  ? "bg-emerald-400"
                  : "border border-white/50"
              }`}
            />
            <span className="truncate">{dm.name}</span>
            {dm.kind === "app" && (
              <span className="rounded bg-white/20 px-1 text-[10px] font-bold uppercase">
                App
              </span>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={onSwitchView}
        className="border-t border-white/10 px-4 py-3 text-left text-xs text-white/70 hover:bg-white/10 hover:text-white"
      >
        ← Switch to web app view
      </button>
    </aside>
  );
}

function SidebarSection({ title }) {
  return (
    <p className="mt-3 mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-white/50">
      {title}
    </p>
  );
}

function ChannelHeader({ name }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 px-5 py-2.5">
      <div className="min-w-0">
        <h1 className="truncate text-[15px] font-black text-slate-900">
          <span className="mr-1 text-slate-400">#</span>
          {name}
        </h1>
        <p className="truncate text-xs text-slate-500">
          Support &amp; operations · 4 members · CPaaS Bot added
        </p>
      </div>
      <span className="hidden shrink-0 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-200 sm:block">
        Simulated Slack UI · fictional data
      </span>
    </header>
  );
}

function ChannelIntro({ name }) {
  return (
    <div className="px-5 pb-4 pt-2">
      <h2 className="text-xl font-black text-slate-900">
        <span className="text-slate-400">#</span>
        {name}
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        This is the very beginning of the <strong>#{name}</strong> channel.
        CPaaS Bot answers questions about numbers, gateways, customers, tickets
        and source lines.
      </p>
    </div>
  );
}

function Composer({ value, onChange, onSubmit, onSuggestion, disabled, channelName }) {
  return (
    <div className="border-t border-slate-200 px-5 py-3">
      <div className="mb-2 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            type="button"
            disabled={disabled}
            onClick={() => onSuggestion(text)}
            className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-600 transition hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50"
          >
            {text}
          </button>
        ))}
      </div>

      <form
        onSubmit={onSubmit}
        className="rounded-lg border border-slate-300 focus-within:border-slate-400"
      >
        <div className="flex items-end gap-2 px-3 py-2">
          <span className="pb-1 font-bold text-slate-400">@</span>
          <input
            value={value}
            onChange={(event) => onChange(event.target.value)}
            disabled={disabled}
            placeholder={`Message #${channelName}`}
            aria-label="Message input"
            className="min-w-0 flex-1 bg-transparent text-[15px] text-slate-800 outline-none placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="rounded bg-[#007a5a] px-2.5 py-1.5 text-white transition hover:bg-[#148567] disabled:bg-slate-200 disabled:text-slate-400"
          >
            <svg viewBox="0 0 20 20" className="h-4 w-4" fill="currentColor">
              <path d="M2 10 18 3l-7 15-2-6-7-2Z" />
            </svg>
          </button>
        </div>
      </form>

      <p className="mt-1.5 text-xs text-slate-400">
        Messages go to the same <code className="font-mono">/query</code> API the
        production Slack bot used.
      </p>
    </div>
  );
}
