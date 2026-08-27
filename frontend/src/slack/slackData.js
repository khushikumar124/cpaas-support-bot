// Static scaffolding for the simulated workspace. Nothing here is a bot
// answer — every bot reply in the transcript comes from the live API.

export const WORKSPACE = "CPaaS Ops";

export const CHANNELS = [
  { id: "support-ops", name: "support-ops", kind: "channel", unread: 0 },
  { id: "vmn-alerts", name: "vmn-alerts", kind: "channel", unread: 3 },
  { id: "gateway-status", name: "gateway-status", kind: "channel", unread: 0 },
  { id: "incidents", name: "incidents", kind: "channel", unread: 1 },
];

export const DIRECT_MESSAGES = [
  { id: "cpaas-bot", name: "CPaaS Bot", kind: "app", presence: "active" },
  { id: "priya", name: "Priya Sharma", kind: "dm", presence: "active" },
  { id: "rahul", name: "Rahul Mehta", kind: "dm", presence: "away" },
];

// Channel chatter that sets the scene. Deliberately contains no bot replies.
export const SEED_MESSAGES = [
  {
    id: "seed-1",
    author: "Priya Sharma",
    initials: "PS",
    color: "bg-[#4A154B]",
    time: "9:41 AM",
    text: "Morning — customer is asking who owns gateway 470, anyone got the sheet open?",
  },
  {
    id: "seed-2",
    author: "Rahul Mehta",
    initials: "RM",
    color: "bg-[#1164A3]",
    time: "9:42 AM",
    text: "just ask the bot, it's faster than opening the sheet",
  },
];

// Fired against the real backend on first load so the channel opens on a
// genuine exchange rather than a hardcoded screenshot.
export const OPENING_QUESTION = "Who owns gateway 470?";

export const SUGGESTIONS = [
  "Show all open tickets",
  "Show all suspended numbers",
  "What is its status?",
  "Show all Vodafone numbers",
  "waht is the staus of 9152001212",
];
