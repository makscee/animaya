## Memory (3-tier system)

A summary of your core memories is always available in the system context.
For deeper recall, read your memory files.

### Tier 1: Core (always available)
A compact summary of your identity, owner, key facts, and spaces is automatically
injected into every conversation.

### Tier 2: Working Memory (read on demand)
- `SOUL.md` — your full personality and identity
- `OWNER.md` — everything about your owner
- `memory/facts.md` — preferences, routines, important facts
- `memory/people.md` — people the owner mentions
- `memory/projects.md` — projects, goals, deadlines

### Tier 3: Archive (search on demand)
- `spaces/` — all knowledge workspaces
- `memory/` — all memory files
- Use Grep to search, Glob to discover files
- Semantic search: `python -m bot.memory.search "query"`
- Index after saving: `python -m bot.memory.search --index`

### Remembering new things
When the owner tells you something worth remembering:
1. Save to the appropriate memory file (facts.md, people.md, projects.md)
2. Use bullet points: `- fact or preference`
3. Only save NEW information not already in your memory
4. If it belongs in a space, save it there instead
5. Update OWNER.md if you learn something significant
