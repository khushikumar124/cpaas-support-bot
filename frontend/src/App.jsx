import { useCallback, useEffect, useMemo, useState } from "react";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import QuickCommandsPanel from "./components/QuickCommandsPanel.jsx";
import Sidebar from "./components/Sidebar.jsx";
import SlackView from "./slack/SlackView.jsx";
import { sendQuery } from "./services/api.js";

const STORAGE_KEY = "cpaas-support-bot.chat-history.v1";
const VIEW_KEY = "cpaas-support-bot.view.v1";

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function titleFromMessage(text) {
  const trimmed = text.trim();
  if (trimmed.length <= 40) return trimmed || "New chat";
  return `${trimmed.slice(0, 40)}...`;
}

function createChat(firstMessage = "") {
  const now = Date.now();
  return {
    id: createId(),
    title: firstMessage ? titleFromMessage(firstMessage) : "New chat",
    messages: [],
    createdAt: now,
    updatedAt: now,
    folderId: null,
  };
}

function createFolder(name) {
  return {
    id: createId(),
    name: name.trim(),
    createdAt: Date.now(),
  };
}

function defaultActiveChatId(chats) {
  if (chats.length === 0) return null;
  return [...chats].sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0))[0].id;
}

function loadSavedWorkspace() {
  if (typeof window === "undefined") {
    return { chats: [], folders: [], activeChatId: null };
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { chats: [], folders: [], activeChatId: null };

    const parsed = JSON.parse(raw);
    const folders = dedupeById(Array.isArray(parsed.folders) ? parsed.folders : [])
      .filter((folder) => folder?.id)
      .map((folder) => ({
        ...folder,
        name: folder.name || "Folder",
        createdAt: folder.createdAt ?? Date.now(),
      }));
    const folderIds = new Set(folders.map((folder) => folder.id));
    const chats = Array.isArray(parsed.chats)
      ? dedupeById(parsed.chats).filter((chat) => chat?.id).map((chat) => ({
          ...chat,
          title: chat.title || "New chat",
          messages: Array.isArray(chat.messages) ? chat.messages : [],
          folderId: folderIds.has(chat.folderId) ? chat.folderId : null,
          createdAt: chat.createdAt ?? Date.now(),
          updatedAt: chat.updatedAt ?? chat.createdAt ?? Date.now(),
        }))
      : [];

    const activeChatId = chats.some((chat) => chat.id === parsed.activeChatId)
      ? parsed.activeChatId
      : defaultActiveChatId(chats);

    return { chats, folders, activeChatId };
  } catch {
    return { chats: [], folders: [], activeChatId: null };
  }
}

function dedupeById(items) {
  const seen = new Set();
  const deduped = [];

  for (const item of items) {
    if (!item?.id || seen.has(item.id)) continue;
    seen.add(item.id);
    deduped.push(item);
  }

  return deduped;
}

export default function App() {
  // The Slack view is the default surface: it is how this bot actually ran in
  // production. The plain web app remains available for a side-by-side look.
  const [view, setView] = useState(() => {
    try {
      return window.localStorage.getItem(VIEW_KEY) ?? "slack";
    } catch {
      return "slack";
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(VIEW_KEY, view);
    } catch {
      /* storage unavailable — the choice just will not persist */
    }
  }, [view]);

  if (view === "slack") {
    return <SlackView onSwitchView={() => setView("web")} />;
  }

  return <WebAppView onSwitchView={() => setView("slack")} />;
}

function WebAppView({ onSwitchView }) {
  const savedWorkspace = useMemo(() => loadSavedWorkspace(), []);
  const [chats, setChats] = useState(savedWorkspace.chats);
  const [folders, setFolders] = useState(savedWorkspace.folders);
  const [activeChatId, setActiveChatId] = useState(savedWorkspace.activeChatId);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingChatId, setPendingChatId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [quickCommandsOpen, setQuickCommandsOpen] = useState(false);
  const [error, setError] = useState(null);

  const activeChat = chats.find((c) => c.id === activeChatId) ?? null;

  useEffect(() => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ chats, folders, activeChatId })
    );
  }, [chats, folders, activeChatId]);

  useEffect(() => {
    if (chats.length === 0) {
      if (activeChatId) setActiveChatId(null);
      return;
    }
    if (activeChatId && chats.some((chat) => chat.id === activeChatId)) return;
    setActiveChatId(defaultActiveChatId(chats));
  }, [activeChatId, chats]);

  const updateChat = useCallback((chatId, updater) => {
    setChats((prev) =>
      prev.map((chat) =>
        chat.id === chatId
          ? { ...updater(chat), updatedAt: Date.now() }
          : chat
      )
    );
  }, []);

  const handleNewChat = () => {
    const chat = createChat();
    setChats((prev) => [chat, ...prev]);
    setActiveChatId(chat.id);
    setInput("");
    setError(null);
    setSidebarOpen(false);
  };

  const handleCreateFolder = (name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setFolders((prev) => {
      const duplicate = prev.some(
        (folder) => folder.name.trim().toLowerCase() === trimmed.toLowerCase()
      );
      return duplicate ? prev : [createFolder(trimmed), ...prev];
    });
  };

  const handleDeleteFolder = (folderId) => {
    setFolders((prev) => prev.filter((folder) => folder.id !== folderId));
    setChats((prev) =>
      prev.map((chat) =>
        chat.folderId === folderId ? { ...chat, folderId: null } : chat
      )
    );
  };

  const handleMoveChat = (chatId, folderId) => {
    updateChat(chatId, (chat) => ({
      ...chat,
      folderId: folderId || null,
    }));
  };

  const handleDeleteChat = (chatId) => {
    setChats((prev) => prev.filter((chat) => chat.id !== chatId));
    setError(null);
  };

  const handleSelectChat = (chatId) => {
    setActiveChatId(chatId);
    setError(null);
    setSidebarOpen(false);
  };

  const handleSelectQuickCommand = (command) => {
    setInput(command);
    setError(null);
    setSidebarOpen(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || isLoading) return;

    let chatId = activeChatId;
    if (!chatId) {
      const chat = createChat(question);
      setChats((prev) => [chat, ...prev]);
      chatId = chat.id;
      setActiveChatId(chatId);
    }

    const userMessage = {
      id: createId(),
      role: "user",
      content: question,
      createdAt: Date.now(),
    };

    updateChat(chatId, (chat) => ({
      ...chat,
      title: chat.messages.length === 0 ? titleFromMessage(question) : chat.title,
      messages: [...chat.messages, userMessage],
    }));

    setInput("");
    setIsLoading(true);
    setPendingChatId(chatId);
    setError(null);

    try {
      const { answer, context_used } = await sendQuery(question, chatId);

      const assistantMessage = {
        id: createId(),
        role: "assistant",
        content: answer,
        contextUsed: context_used ?? false,
        createdAt: Date.now(),
      };

      updateChat(chatId, (chat) => ({
        ...chat,
        messages: [...chat.messages, assistantMessage],
      }));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to reach the server.";
      setError(message);
      updateChat(chatId, (chat) => ({
        ...chat,
        messages: [
          ...chat.messages,
          {
            id: createId(),
            role: "assistant",
            content: `Sorry, something went wrong: ${message}`,
            createdAt: Date.now(),
          },
        ],
      }));
    } finally {
      setIsLoading(false);
      setPendingChatId(null);
    }
  };

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar
        chats={chats}
        folders={folders}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onCreateFolder={handleCreateFolder}
        onDeleteFolder={handleDeleteFolder}
        onMoveChat={handleMoveChat}
        onDeleteChat={handleDeleteChat}
        onOpenQuickCommands={() => setQuickCommandsOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <QuickCommandsPanel
        isOpen={quickCommandsOpen}
        onClose={() => setQuickCommandsOpen(false)}
        onSelectCommand={handleSelectQuickCommand}
      />

      <div className="flex min-w-0 flex-1 flex-col bg-slate-50">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 shadow-sm sm:px-6">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
            aria-label="Open menu"
          >
            <MenuIcon />
          </button>
          <h1 className="truncate text-sm font-semibold text-slate-800 sm:text-base">
            {activeChat?.title ?? "CPaaS Support Assistant"}
          </h1>
          <button
            type="button"
            onClick={onSwitchView}
            className="ml-auto shrink-0 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
          >
            View as Slack →
          </button>
        </header>

        {error && (
          <div
            className="mx-4 mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 sm:mx-6"
            role="alert"
          >
            {error}
          </div>
        )}

        <ChatWindow
          messages={activeChat?.messages ?? []}
          isLoading={isLoading && activeChatId === pendingChatId}
          onSelectExample={handleSelectQuickCommand}
        />

        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={handleSubmit}
          disabled={isLoading}
        />
      </div>
    </div>
  );
}

function MenuIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      className="h-6 w-6"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
      />
    </svg>
  );
}
