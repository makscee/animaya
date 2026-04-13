# Feature Landscape

**Domain:** Modular personal AI assistant platform (Telegram bridge + web dashboard + installable modules)
**Researched:** 2026-04-13

## Table Stakes

Features users expect from any personal AI assistant. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Streaming responses | Latency feels unbearable without it; all major assistants stream | Low | Already proven in v1 |
| Persistent memory across sessions | Without it users repeat themselves constantly; kills trust | Medium | Core differentiator for personal assistant vs. chatbot |
| Telegram bridge | Primary interface; users already live in Telegram | Low | Core, not a module |
| Web dashboard for configuration | Users need somewhere to see and control the assistant | Medium | Core, not a module |
| Identity/onboarding | Assistant must know who the user is; cold-start is jarring | Low | Module (identity) |
| Reliable message delivery | Messages must not silently fail; errors must surface | Low | Bridge concern |
| Module install/uninstall without breaking core | Modular systems live or die on clean isolation | Medium | Architectural constraint |

## Differentiators

Features that set Animaya apart. Not expected by default, but create loyalty and word-of-mouth.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Git-versioned memory | Full audit trail of what the assistant knows about you; rollback; portable | Medium | Hub-native, strong technical differentiator |
| Markdown-file memory (Hub-style) | Human-readable, editable without the app, works with any git tool | Low | Fits existing Voidnet/Hub ecosystem |
| Module marketplace feel (folder + manifest) | Users can share, copy, or inspect modules; no black boxes | Medium | Transparent extensibility beats opaque plugin stores |
| Reversible modules (clean uninstall) | Reduces fear of trying new modules; builds trust | Medium | Required by constraints; becomes a differentiator in practice |
| LXC-native (no Docker overhead) | Simpler ops, no nested virtualization, direct Proxmox integration | Low | Infrastructure differentiator for Voidnet users |
| Voidnet integration (provision from web UI) | One-click assistant spin-up within ecosystem; no CLI needed | High | Requires Voidnet platform work; big onboarding win |
| Skill files (~skill.md) | Users can teach the assistant reusable procedures | Medium | Familiar pattern from Hub; extends memory module |
| Per-module configuration stored in Hub | Module state is auditable, portable, shareable via git | Low | Follows Hub convention; zero extra infra |

## Anti-Features

Features to explicitly NOT build in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Semantic / vector search over memory | High ops complexity (embeddings infra), distraction from core loop | Keyword/grep search over markdown files is good enough for v1 |
| Image generation | Nice-to-have; module can be added post-v1 | Defer to an image-gen module |
| Voice transcription | Same: nice-to-have, adds API key management complexity | Defer to a voice module |
| Plugin inter-dependencies | Causes cascading failures on uninstall; proven anti-pattern | Each module reads files directly; no module imports another |
| Multi-user provisioning UI inside Animaya | Voidnet handles this; Animaya should stay single-user | Let Voidnet's web interface own provisioning |
| Custom marketplace/registry | Overhead without enough modules to justify | Plain git repos + folder-drop installs are sufficient for v1 |
| Runtime pip / package install in bot process | Security risk; unpredictable environments | Modules declare dependencies in their manifest; installed at setup time |
| Real-time collaboration or shared assistants | Scope creep; personal assistant = one user | Each Claude Box is one user's assistant |

## Feature Dependencies

```
Telegram bridge (core)
  └─ Streaming responses (bridge concern)
  └─ Reliable delivery / error surfacing

Web dashboard (core)
  └─ Module install/uninstall UI
      └─ Module system (folder + manifest)
          └─ Identity module (who is the user, who is the assistant)
          └─ Memory module (Hub-style knowledge/ structure)
              └─ Git versioning module (auto-commit data changes)
              └─ [future] Skill files (~skill.md)
              └─ [future] Semantic search module
          └─ [future] Voice module
          └─ [future] Image generation module
```

## MVP Recommendation

Prioritize for v1:

1. **Telegram bridge + streaming** — core; nothing works without it
2. **Web dashboard** — configuration surface; required for module management
3. **Module system** — folder + manifest install/uninstall; architectural foundation everything else builds on
4. **Identity module** — onboarding, who-is-the-user; eliminates cold-start problem
5. **Memory module** — Hub-style knowledge/ structure; what transforms a chatbot into a personal assistant
6. **Git versioning module** — auto-commit /data; makes memory auditable and reversible

Defer to post-v1 modules:
- Voice transcription: real module candidate, low urgency
- Image generation: real module candidate, low urgency
- Semantic search: only worth adding once memory corpus is large enough to need it
- Skill files: natural extension of memory module; add when memory module is stable

## Sources

- [Clawdbot Explained: Self-Hosted AI Assistant With Persistent Memory](https://aiagentsdirectory.com/blog/clawdbot-explained-the-self-hosted-ai-assistant-that-can-actually-do-things) — MEDIUM confidence (community blog, verified against OpenClaw GitHub)
- [OpenClaw GitHub](https://github.com/openclaw/openclaw) — MEDIUM confidence (closest comparable project)
- [Building a Plugin Marketplace for AI-Native Workflows](https://www.mpt.solutions/building-a-plugin-marketplace-for-ai-native-workflows/) — MEDIUM confidence (practitioner article)
- [Plugin architecture — no inter-plugin dependencies pattern](https://arjancodes.com/blog/best-practices-for-decoupling-software-using-plugins/) — HIGH confidence (well-established software pattern)
- [What Is Modular AI Architecture?](https://magai.co/what-is-modular-ai-architecture/) — MEDIUM confidence
- Animaya v1 prior art (this repo) — HIGH confidence for what was proven to work
