# Codebase Concerns

**Analysis Date:** 2026-04-13

## Tech Debt

**Dashboard Logging Not Implemented:**
- Issue: `/api/logs` endpoint returns empty array with TODO comment
- Files: `bot/dashboard/app.py:415`
- Impact: Users cannot view bot logs through dashboard; troubleshooting requires direct file access
- Fix approach: Implement logging handler that captures Python logs into in-memory buffer, expose via API endpoint with configurable level and limit

**SDK Message Parser Patching:**
- Issue: Monkey-patching `claude_code_sdk._internal.message_parser.parse_message` to suppress "Unknown message type" errors
- Files: `bot/bridge/telegram.py:46-69`
- Impact: Hides SDK bugs; fragile if SDK internals change; silent failures mask real issues
- Fix approach: Report this to Anthropic; use SDK's error callback instead of patching internals once available

**Memory Search Sidecar Files Not Tracked:**
- Issue: Embedding sidecar files (`.*.embeddings.json`) created alongside markdown files but not committed or version-controlled
- Files: `bot/memory/search.py:94-96, 154`
- Impact: Embedding cache loss on container rebuild; stale embeddings after manual file edits
- Fix approach: Add sidecar cleanup on startup, or commit embeddings into git version control with file hash validation

**Dashboard CORS Allows All Origins:**
- Issue: `allow_origins=["*"]` permissive CORS middleware
- Files: `bot/dashboard/app.py:23-28`
- Impact: Cross-site request attacks possible if dashboard token is leaked or guessed
- Fix approach: Restrict to specific origins (platform domain, localhost), require CSRF tokens for state-changing requests

## Known Bugs

**Streaming Text Truncation Without Warning:**
- Symptoms: Messages longer than 4096 chars silently split; last chunk may exceed limit
- Files: `bot/bridge/telegram.py:265-269, 331-340`
- Trigger: Send reply >4096 characters from Claude
- Workaround: None; accepts silent split; users may not notice incomplete text
- Fix approach: Add explicit "message too long" warning before splitting, or use Telegram's document/file API

**Daemon Thread Loses Graceful Shutdown:**
- Symptoms: Dashboard uvicorn thread (daemon=True) killed abruptly on SIGTERM without cleanup
- Files: `bot/main.py:71`
- Trigger: Container restart or stop signal
- Workaround: Only affects in-flight HTTP requests
- Fix approach: Use proper thread coordination or async application startup/shutdown lifecycle

**Event Queue Overflow Silent Loss:**
- Symptoms: SSE client may miss events if browser falls behind; QueueFull exceptions caught and silently dropped
- Files: `bot/dashboard/app.py:36-41`
- Trigger: Slow client connection during high-volume streaming
- Workaround: None; users see partial chat history
- Fix approach: Use bounded queue with backpressure or drop oldest events, log drops

## Security Considerations

**Dashboard Authentication Weak When Token Not Set:**
- Risk: Anyone with network access can use API if `DASHBOARD_TOKEN` env var missing
- Files: `bot/dashboard/auth.py:22-23`
- Current mitigation: Decorator bypasses auth if token not configured
- Recommendations: Default to deny-all if no token configured; require explicit `--insecure-no-auth` flag for development

**API Keys Exposed in Default Config:**
- Risk: `GOOGLE_API_KEY`, `EMBEDDING_API_KEY`, `STT_API_KEY` logged or exposed in error messages
- Files: `bot/features/image_gen.py:19`, `bot/features/audio.py:18`, `bot/memory/search.py:75`
- Current mitigation: None; keys appear in HTTP error responses
- Recommendations: Mask API keys in error messages; use structured logging that filters secrets

**File Send Regex May Execute Path Traversal:**
- Risk: Regex pattern `_FILE_PATH_RE` matches paths starting with `/data/`; no validation against symlinks or directory traversal
- Files: `bot/bridge/telegram.py:362`
- Current mitigation: Path must exist on filesystem
- Recommendations: Validate resolved path is under `/data/`; check for symlink attacks; add `.gitignore` style exclusions

**Token Passing in URL Query Params:**
- Risk: Dashboard auth token can be passed in query string, logged by proxies, appear in browser history
- Files: `bot/dashboard/auth.py:27`
- Current mitigation: Also accepts Bearer header (preferred)
- Recommendations: Remove query param support; warn users if query param auth used; only accept Authorization header

## Performance Bottlenecks

**Git Auto-Commit Blocking on Large Repos:**
- Problem: `subprocess.run()` blocks event loop during git operations; 30-second timeout may not be enough for large diffs
- Files: `bot/features/git_versioning.py:27-40`
- Cause: Synchronous subprocess in async context; no async git wrapper
- Improvement path: Use `asyncio.create_subprocess_exec()` or `ThreadPoolExecutor` for git ops

**Embedding API Calls Not Batched Efficiently:**
- Problem: Each file reindexed calls `_embed_batch()` for only changed chunks; no request coalescing across files
- Files: `bot/memory/search.py:125-141`
- Cause: Linear iteration over markdown files, one-by-one API calls
- Improvement path: Collect all chunks to embed, batch into single API call; implement concurrent indexing

**Memory Search Vector Cosine Distance Computed for All Chunks:**
- Problem: Search scores every chunk in memory even if corpus is large; no approximate nearest neighbor
- Files: `bot/memory/search.py:170+` (not shown, but implied)
- Cause: Full linear scan; embeddings stored in JSON sidecars
- Improvement path: Use vector DB (pgvector, Chroma) or implement approximate search (LSH, FAISS)

**Dashboard History Loads All Messages on Every Request:**
- Problem: `/api/chat/history` loads entire history JSON, filters in Python, returns subset
- Files: `bot/dashboard/app.py:269-277`
- Cause: No pagination, filtering, or indexing
- Improvement path: Implement range queries, add filter indexes, paginate results

## Fragile Areas

**Telegram Message Forwarding Handling:**
- Files: `bot/bridge/telegram.py:161-169`
- Why fragile: Accesses optional attributes (sender_user, sender_user_name, chat) with hasattr checks; no unit tests; message_thread_id retrieval is getattr-based
- Safe modification: Add integration tests for group chats, forwarded messages, forum threads; add type guards
- Test coverage: No tests for message envelope construction

**Memory Consolidation Relies on Claude Following Exact Instructions:**
- Files: `bot/memory/core.py:65-80`
- Why fragile: Post-conversation consolidation prompt (in docstring) depends on Claude parsing and executing rules; no validation
- Safe modification: Implement post-processing to validate memory file format; use structured output (JSON) from Claude
- Test coverage: No tests for memory file validation

**SDK Message Type Patching Suppresses Errors:**
- Files: `bot/bridge/telegram.py:46-69`
- Why fragile: SDK version updates may change internal structure; patching suppresses legitimate errors
- Safe modification: Add SDK version check; raise exception if patch fails; maintain SDK fork if needed
- Test coverage: No tests for SDK compatibility

**Config JSON Parsing Unvalidated:**
- Files: `bot/claude_query.py:50-56`, `bot/dashboard/app.py:88-92`, `bot/bridge/telegram.py:277-281`
- Why fragile: Silent fallback on parse errors; missing keys assumed to be defaults; no schema validation
- Safe modification: Use Pydantic models for config; fail loudly if invalid; migrate old formats
- Test coverage: No tests for malformed config

## Scaling Limits

**User Lock Dictionary Unbounded:**
- Current capacity: Up to N users * 1 asyncio.Lock per user
- Limit: No cleanup; old locks for inactive users accumulate indefinitely
- Files: `bot/bridge/telegram.py:79-83`
- Scaling path: Implement LRU cache for user locks; periodically prune inactive users; add cleanup on user block

**In-Memory Event Queues:**
- Current capacity: `maxsize=100` per connected SSE client
- Limit: Multiple clients = multiple queues; memory grows with concurrent users
- Files: `bot/dashboard/app.py:33, 246`
- Scaling path: Use shared event bus (Redis, RabbitMQ) instead of in-process queues

**Git Auto-Commit on Single Thread:**
- Current capacity: One commit at a time, every 300 seconds
- Limit: Large repositories may exceed interval; commits block shutdown
- Files: `bot/features/git_versioning.py:64-78`
- Scaling path: Use async git operations; implement git gc scheduling

**Markdown File Indexing Sequential:**
- Current capacity: One file at a time, API calls blocking
- Limit: 100+ markdown files = 100+ API calls; indexing takes minutes
- Files: `bot/memory/search.py:157-169`
- Scaling path: Concurrent indexing with asyncio; batch embedding requests

## Dependencies at Risk

**Claude Code SDK Tight Integration:**
- Risk: Monkey-patching internals; relies on SDK message types; tight coupling to query() API
- Files: `bot/bridge/telegram.py:46-69`, `bot/claude_query.py:31`, `bot/dashboard/app.py:215-236`
- Impact: SDK breaking changes break bot; message format changes lose tool tracking
- Migration plan: Maintain compatibility shim layer; use SDK stable APIs only; implement version check on startup

**Python-Telegram-Bot Library:**
- Risk: Async library with complex state management; forward_origin handling assumes library internals
- Files: `bot/bridge/telegram.py:162-169`
- Impact: Library updates may change message attributes; group chat handling fragile
- Migration plan: Add message validation layer; test against new library versions before upgrading

**Groq/OpenAI API for Embeddings:**
- Risk: Embedding API changes (model retirement, rate limits) break memory search
- Files: `bot/memory/search.py:73-86`
- Impact: Semantic search fails; no fallback
- Migration plan: Support multiple embedding providers; cache embeddings indefinitely; implement graceful degradation

## Missing Critical Features

**No Error Recovery for Failed Queries:**
- Problem: Claude Code query fails → message incomplete; no retry or error context sent to user
- Blocks: Users can't diagnose why assistant stopped responding
- Files: `bot/bridge/telegram.py:410+` (message handler)
- Fix approach: Catch exceptions, send error message, optionally retry with shorter context

**No Rate Limiting:**
- Problem: Users can spam queries without limit; no per-user rate limiting
- Blocks: Resource exhaustion; DOS vulnerability
- Files: `bot/bridge/telegram.py` (message handler has no rate limit checks)
- Fix approach: Implement token bucket or sliding window rate limiter; configurable per user

**No Conversation Context Cleanup:**
- Problem: Memory grows indefinitely; old conversations stay in memory files
- Blocks: Long-running bots accumulate stale data; semantic search becomes noisy
- Files: `bot/memory/` (no archival mechanism)
- Fix approach: Implement memory archival; move old conversations to separate storage; add TTL to facts

**No Audit Logging:**
- Problem: No record of who sent what to Claude; no consent/compliance tracking
- Blocks: Cannot audit for PII exposure; no data provenance
- Files: `bot/dashboard/app.py` (message logging exists but no access control audit)
- Fix approach: Implement audit trail; log message source, user, timestamp, model used

## Test Coverage Gaps

**No Tests for Telegram Message Processing:**
- What's not tested: Message envelope construction, forwarded messages, group chat handling, file sending, rate limiting
- Files: `bot/bridge/telegram.py`
- Risk: Telegram API changes break message handling silently
- Priority: High (core functionality)

**No Tests for Memory Search:**
- What's not tested: Chunk splitting, embedding vector normalization, similarity ranking, file indexing
- Files: `bot/memory/search.py`
- Risk: Search results become irrelevant if chunking or vector logic breaks
- Priority: High (affects user experience)

**No Tests for Dashboard API:**
- What's not tested: Chat streaming, SSE event flow, message history filtering, module management
- Files: `bot/dashboard/app.py`
- Risk: Web UI breaks silently; streaming errors not caught
- Priority: Medium (web UI is secondary to Telegram)

**No Tests for Git Versioning:**
- What's not tested: Commit conditions, diff detection, shutdown handling, concurrent access
- Files: `bot/features/git_versioning.py`
- Risk: Data loss if commit logic breaks; git corrupted state unnoticed
- Priority: High (data integrity)

**No Tests for Config and Auth:**
- What's not tested: Config parsing, auth decorator behavior, token validation, default fallback
- Files: `bot/dashboard/auth.py`, `bot/claude_query.py` (config parsing)
- Risk: Silent config failures; auth bypass unnoticed
- Priority: Medium (affects security)

---

*Concerns audit: 2026-04-13*
