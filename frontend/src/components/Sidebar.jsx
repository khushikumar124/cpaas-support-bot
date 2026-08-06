import { useMemo, useState } from "react";

/**
 * Left sidebar with persisted chat history and folder organization.
 */
export default function Sidebar({
  chats,
  folders,
  activeChatId,
  onSelectChat,
  onNewChat,
  onCreateFolder,
  onDeleteFolder,
  onMoveChat,
  onDeleteChat,
  onOpenQuickCommands,
  isOpen,
  onClose,
}) {
  const [isCreatingFolder, setIsCreatingFolder] = useState(false);
  const [folderName, setFolderName] = useState("");

  const sortedChats = useMemo(
    () => [...chats].sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0)),
    [chats]
  );

  const chatsByFolder = useMemo(() => {
    const grouped = new Map();
    for (const folder of folders) grouped.set(folder.id, []);
    grouped.set(null, []);

    for (const chat of sortedChats) {
      const key = folders.some((folder) => folder.id === chat.folderId)
        ? chat.folderId
        : null;
      grouped.get(key).push(chat);
    }

    return grouped;
  }, [folders, sortedChats]);

  const handleCreateFolder = (e) => {
    e.preventDefault();
    const trimmed = folderName.trim();
    if (!trimmed) return;

    onCreateFolder(trimmed);
    setFolderName("");
    setIsCreatingFolder(false);
  };

  const handleDeleteFolder = (folderId) => {
    const ok = window.confirm(
      "Delete this folder? Its chats will stay in History."
    );
    if (ok) onDeleteFolder(folderId);
  };

  const handleDeleteChat = (chatId) => {
    const ok = window.confirm("Delete this chat from history?");
    if (ok) onDeleteChat(chatId);
  };

  return (
    <>
      {isOpen && (
        <button
          type="button"
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={onClose}
          aria-label="Close sidebar"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-80 max-w-[86vw] flex-col bg-slate-900 text-slate-100 transition-transform duration-200 lg:static lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 border-b border-slate-700/80 px-4 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-600 text-sm font-bold text-white">
            C
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold">CPaaS Support Bot</p>
            <p className="truncate text-xs text-slate-400">
              Demo build · fictional data
            </p>
          </div>
        </div>

        <div className="space-y-2 p-3">
          <button
            type="button"
            onClick={onNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            <PlusIcon />
            New chat
          </button>

          <button
            type="button"
            onClick={onOpenQuickCommands}
            className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
          >
            <CommandIcon />
            Quick Commands
          </button>

          {isCreatingFolder ? (
            <form onSubmit={handleCreateFolder} className="flex gap-2">
              <input
                value={folderName}
                onChange={(e) => setFolderName(e.target.value)}
                autoFocus
                placeholder="Folder name"
                className="min-w-0 flex-1 rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-teal-500 focus:outline-none"
              />
              <button
                type="submit"
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-white hover:bg-teal-600"
                aria-label="Save folder"
              >
                <CheckIcon />
              </button>
              <button
                type="button"
                onClick={() => {
                  setFolderName("");
                  setIsCreatingFolder(false);
                }}
                className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800"
                aria-label="Cancel folder"
              >
                <CloseIcon />
              </button>
            </form>
          ) : (
            <button
              type="button"
              onClick={() => setIsCreatingFolder(true)}
              className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
            >
              <FolderPlusIcon />
              New folder
            </button>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-4">
          {chats.length === 0 ? (
            <p className="px-3 py-4 text-sm text-slate-500">No conversations yet</p>
          ) : (
            <div className="space-y-4">
              {folders.map((folder) => (
                <ChatSection
                  key={folder.id}
                  title={folder.name}
                  chats={chatsByFolder.get(folder.id) ?? []}
                  folders={folders}
                  activeChatId={activeChatId}
                  onSelectChat={onSelectChat}
                  onMoveChat={onMoveChat}
                  onDeleteChat={handleDeleteChat}
                  onDeleteFolder={() => handleDeleteFolder(folder.id)}
                />
              ))}

              <ChatSection
                title="History"
                chats={chatsByFolder.get(null) ?? []}
                folders={folders}
                activeChatId={activeChatId}
                onSelectChat={onSelectChat}
                onMoveChat={onMoveChat}
                onDeleteChat={handleDeleteChat}
              />
            </div>
          )}
        </nav>

        <div className="border-t border-slate-700/80 px-4 py-3 text-xs text-slate-500">
          Portfolio demo · fictional data
        </div>
      </aside>
    </>
  );
}

function ChatSection({
  title,
  chats,
  folders,
  activeChatId,
  onSelectChat,
  onMoveChat,
  onDeleteChat,
  onDeleteFolder,
}) {
  if (chats.length === 0 && title !== "History") {
    return (
      <section>
        <SectionHeader title={title} onDeleteFolder={onDeleteFolder} />
        <p className="px-3 py-2 text-xs text-slate-500">No chats</p>
      </section>
    );
  }

  return (
    <section>
      <SectionHeader title={title} onDeleteFolder={onDeleteFolder} />
      {chats.length === 0 ? (
        <p className="px-3 py-2 text-xs text-slate-500">No conversations yet</p>
      ) : (
        <ul className="space-y-1">
          {chats.map((chat) => (
            <li
              key={chat.id}
              className={`rounded-lg ${
                chat.id === activeChatId
                  ? "bg-slate-700 text-white"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <button
                type="button"
                onClick={() => onSelectChat(chat.id)}
                className="w-full truncate px-3 pb-1.5 pt-2.5 text-left text-sm"
              >
                {chat.title}
              </button>
              <div className="flex items-center gap-1 px-2 pb-2">
                <select
                  value={chat.folderId ?? ""}
                  onChange={(e) => onMoveChat(chat.id, e.target.value || null)}
                  className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-300 focus:border-teal-500 focus:outline-none"
                  aria-label={`Move ${chat.title}`}
                >
                  <option value="">History</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>
                      {folder.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => onDeleteChat(chat.id)}
                  className="flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-700 hover:text-white"
                  aria-label={`Delete ${chat.title}`}
                >
                  <TrashIcon />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SectionHeader({ title, onDeleteFolder }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2">
      <p className="min-w-0 flex-1 truncate text-xs font-medium uppercase tracking-wide text-slate-500">
        {title}
      </p>
      {onDeleteFolder && (
        <button
          type="button"
          onClick={onDeleteFolder}
          className="flex h-6 w-6 items-center justify-center rounded-md text-slate-500 hover:bg-slate-800 hover:text-slate-200"
          aria-label={`Delete folder ${title}`}
        >
          <TrashIcon />
        </button>
      )}
    </div>
  );
}

function PlusIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z" />
    </svg>
  );
}

function FolderPlusIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M3.5 4A2.5 2.5 0 0 0 1 6.5v7A2.5 2.5 0 0 0 3.5 16h13a2.5 2.5 0 0 0 2.5-2.5v-6A2.5 2.5 0 0 0 16.5 5H9.621a1.5 1.5 0 0 1-1.06-.44L7.94 3.94A1.5 1.5 0 0 0 6.879 3.5H3.5V4Zm7.25 4.25a.75.75 0 0 0-1.5 0v1h-1a.75.75 0 0 0 0 1.5h1v1a.75.75 0 0 0 1.5 0v-1h1a.75.75 0 0 0 0-1.5h-1v-1Z" />
    </svg>
  );
}

function CommandIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path
        fillRule="evenodd"
        d="M2 5.25A2.25 2.25 0 0 1 4.25 3h11.5A2.25 2.25 0 0 1 18 5.25v9.5A2.25 2.25 0 0 1 15.75 17H4.25A2.25 2.25 0 0 1 2 14.75v-9.5Zm3.5 1.5a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 0-1.5h-3Zm0 3a.75.75 0 0 0 0 1.5h9a.75.75 0 0 0 0-1.5h-9Zm0 3a.75.75 0 0 0 0 1.5h6a.75.75 0 0 0 0-1.5h-6Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path
        fillRule="evenodd"
        d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.25 7.31a1 1 0 0 1-1.421 0L3.29 9.224a1 1 0 1 1 1.42-1.408l4.039 4.074 6.54-6.594a1 1 0 0 1 1.414-.006Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-3.5 w-3.5"
    >
      <path
        fillRule="evenodd"
        d="M8.75 1.5A1.75 1.75 0 0 0 7 3.25V4H4.25a.75.75 0 0 0 0 1.5h.5l.7 10.08A2.25 2.25 0 0 0 7.695 17.5h4.61a2.25 2.25 0 0 0 2.244-1.92l.701-10.08h.5a.75.75 0 0 0 0-1.5H13v-.75a1.75 1.75 0 0 0-1.75-1.75h-2.5ZM8.5 4v-.75A.25.25 0 0 1 8.75 3h2.5a.25.25 0 0 1 .25.25V4h-3Z"
        clipRule="evenodd"
      />
    </svg>
  );
}
