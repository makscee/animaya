## Spaces (Knowledge Workspaces)

Spaces organize knowledge by topic. Each space is a folder in `/data/spaces/` prefixed with `@`.

### Structure
```
/data/spaces/
├── _index.md                    # Master index
├── @gamedev/
│   ├── _meta.md                 # YAML frontmatter + description
│   ├── _index.md                # File catalog (pipe-separated)
│   ├── _log.md                  # Activity log
│   └── character-design.md
└── @cooking/
    ├── _meta.md
    ├── _index.md
    ├── _log.md
    └── favorite-recipes.md
```

### Creating a space
Create these three system files:

**`_meta.md`**:
```
---
access_count: 0
created: '2026-01-01'
last_active: '2026-01-01'
status: active
tags: []
---
Description of the space.
```

**`_index.md`**: `filename | description` (one per line, NOT tables)

**`_log.md`**: `2026-01-01 14:00 | created space`

### Working with spaces
- When user mentions @space-name, read its `_index.md` to load context
- Active space = default storage for new files
- After changes, update `_index.md` and `_log.md`
- Track access in `_meta.md` (increment `access_count`, set `last_active`)

### Rules
- Names MUST start with `@`, use kebab-case
- Max nesting: 3 levels
- `_index.md` format: `filename | description` (pipe-separated)
- Always create all three system files
- Update `_log.md` on every change

## Skills (Evolving Procedures)

Skills are reusable procedures as `~`-prefixed files inside spaces.

### Format
```markdown
---
version: 1
created: '2026-01-01'
evolved: '2026-01-01'
failures: 0
---
# Skill Name

## Steps
1. Step one
2. Step two

## Notes
- Important notes
```

### When to create
- After successfully handling a complex multi-step task
- When a procedure repeats 2+ times
- Proactively suggest: "Want me to save this as a skill?"

### Evolving skills
When corrected: update the skill, increment version, note what changed.
After 3+ failures: rewrite the entire skill incorporating lessons learned.
