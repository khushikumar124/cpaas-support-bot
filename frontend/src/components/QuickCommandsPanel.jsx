import quickCommandGroups from "../config/quickCommands.js";

export default function QuickCommandsPanel({ isOpen, onClose, onSelectCommand }) {
  if (!isOpen) return null;

  const handleSelect = (command) => {
    onSelectCommand(command);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-center bg-slate-950/40 px-4 py-16 sm:py-20">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        onClick={onClose}
        aria-label="Close quick commands"
      />

      <section
        className="relative z-10 w-full max-w-2xl overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"
        aria-modal="true"
        role="dialog"
        aria-labelledby="quick-commands-title"
      >
        <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-700 text-white">
            <CommandIcon />
          </div>
          <div className="min-w-0 flex-1">
            <h2
              id="quick-commands-title"
              className="truncate text-base font-semibold text-slate-800"
            >
              Quick Commands
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            aria-label="Close quick commands"
          >
            <CloseIcon />
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-5 py-4">
          <div className="grid gap-4 sm:grid-cols-3">
            {quickCommandGroups.map((group) => (
              <section key={group.title} className="min-w-0">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {group.title}
                </h3>
                <div className="space-y-2">
                  {group.commands.map((command) => (
                    <button
                      key={command}
                      type="button"
                      onClick={() => handleSelect(command)}
                      className="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm leading-snug text-slate-700 transition hover:border-teal-200 hover:bg-teal-50 hover:text-slate-900"
                    >
                      {command}
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function CommandIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-5 w-5"
    >
      <path
        fillRule="evenodd"
        d="M2 5.25A2.25 2.25 0 0 1 4.25 3h11.5A2.25 2.25 0 0 1 18 5.25v9.5A2.25 2.25 0 0 1 15.75 17H4.25A2.25 2.25 0 0 1 2 14.75v-9.5Zm3.5 1.5a.75.75 0 0 0 0 1.5h3a.75.75 0 0 0 0-1.5h-3Zm0 3a.75.75 0 0 0 0 1.5h9a.75.75 0 0 0 0-1.5h-9Zm0 3a.75.75 0 0 0 0 1.5h6a.75.75 0 0 0 0-1.5h-6Z"
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
      className="h-5 w-5"
    >
      <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
    </svg>
  );
}
