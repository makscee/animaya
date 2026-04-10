import type { Module } from "./types";

export const MODULE_DEFINITIONS: Module[] = [
  {
    id: "identity",
    name: "Identity",
    description: "Give your bot a personality. Creates SOUL.md and OWNER.md through a guided conversation.",
    icon: "🪪",
    category: "core",
    installSteps: [
      { title: "Bot Name", description: "What should your assistant be called?", type: "input", field: "botName", placeholder: "e.g., Aria, Helper, Max..." },
      { title: "Your Name", description: "What's your name? The bot will remember you as its owner.", type: "input", field: "ownerName", placeholder: "Your name" },
      { title: "Personality", description: "How should your bot communicate? (e.g., friendly and casual, professional, witty)", type: "input", field: "personality", placeholder: "e.g., friendly, concise, uses humor" },
      { title: "Language", description: "What language should the bot primarily use?", type: "input", field: "language", placeholder: "e.g., English, Russian, Spanish" },
      { title: "Purpose", description: "What will you mainly use this bot for?", type: "input", field: "purpose", placeholder: "e.g., personal assistant, work helper, learning..." },
    ],
  },
  {
    id: "telegram",
    name: "Telegram",
    description: "Connect your bot to Telegram. Chat with it from your phone anytime.",
    icon: "✈️",
    category: "integration",
    installSteps: [
      { title: "Create a Bot", description: "Open @BotFather on Telegram, send /newbot, and follow the instructions. Copy the token it gives you.", type: "info" },
      { title: "Bot Token", description: "Paste your Telegram bot token here.", type: "input", field: "botToken", placeholder: "123456789:ABCdefGHIjklMNO..." },
    ],
  },
  {
    id: "memory",
    name: "Memory",
    description: "3-tier memory system. Your bot remembers facts, people, and projects across conversations.",
    icon: "🧠",
    category: "core",
    installSteps: [
      { title: "Enable Memory", description: "This will create memory files and add memory instructions to your bot. It will remember things you tell it.", type: "confirm" },
    ],
  },
  {
    id: "spaces",
    name: "Spaces",
    description: "Knowledge workspaces. Organize information by topic with @space-name folders.",
    icon: "📂",
    category: "feature",
    requires: ["memory"],
    installSteps: [
      { title: "Enable Spaces", description: "Spaces let you organize knowledge by topic. Your bot can create @project-name workspaces and evolving skills.", type: "confirm" },
    ],
  },
  {
    id: "github",
    name: "GitHub Sync",
    description: "Sync your bot's data to a GitHub repository for backup and version control.",
    icon: "🐙",
    category: "integration",
    installSteps: [
      { title: "Repository", description: "Enter the GitHub repository to sync to (e.g., username/my-bot-data).", type: "input", field: "repo", placeholder: "username/repo" },
      { title: "Access Token", description: "Create a GitHub personal access token with repo scope and paste it here.", type: "input", field: "githubToken", placeholder: "ghp_..." },
    ],
  },
  {
    id: "voice",
    name: "Voice Messages",
    description: "Transcribe voice messages using Whisper. Works in Telegram and web chat.",
    icon: "🎤",
    category: "feature",
    installSteps: [
      { title: "Groq API Key", description: "Voice transcription uses Groq's Whisper API (free tier available). Get a key at console.groq.com.", type: "input", field: "sttApiKey", placeholder: "gsk_..." },
    ],
  },
  {
    id: "image-gen",
    name: "Image Generation",
    description: "Generate images using Google Gemini. Your bot can create visuals on request.",
    icon: "🎨",
    category: "feature",
    installSteps: [
      { title: "Google API Key", description: "Get a Gemini API key at aistudio.google.com. Paste it here.", type: "input", field: "googleApiKey", placeholder: "AIza..." },
    ],
  },
  {
    id: "self-dev",
    name: "Self-Development",
    description: "Let your bot install packages and write custom tools via bot.Dockerfile.",
    icon: "🔧",
    category: "feature",
    installSteps: [
      { title: "Enable Self-Dev", description: "Your bot will be able to manage its own packages via bot.Dockerfile (no direct pip install — everything is versioned and rebuildable).", type: "confirm" },
    ],
  },
];
