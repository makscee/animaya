# Testing Patterns

**Analysis Date:** 2026-04-13

## Test Framework

**Runner:**
- pytest 8.0+ 
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- pytest built-in assertions (no separate library)

**Run Commands:**
```bash
python -m pytest tests/ -v              # Run all tests with verbose output
python -m pytest tests/ -v -s           # Run with stdout printing
python -m pytest tests/ -v --cov=bot    # Run with coverage report
```

**Configuration (pyproject.toml):**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Test File Organization

**Current Status:**
- No test directory present in codebase (only `pyproject.toml` declares test config)
- Test infrastructure exists but no test files found

**When tests are added:**

**Location:**
- Co-located: Tests near code being tested
- Separate directory structure: `tests/` at project root matching `bot/` structure

**Naming:**
- `test_<module>.py` for unit tests: `test_telegram.py`, `test_memory.py`
- `test_<feature>_integration.py` for integration tests

**Structure:**
```
tests/
├── test_audio.py
├── test_search.py
├── test_memory/
│   ├── __init__.py
│   ├── test_core.py
│   └── test_search.py
├── bridge/
│   ├── __init__.py
│   └── test_telegram.py
└── conftest.py
```

## Async Testing

**Pattern (pytest-asyncio):**

Since `asyncio_mode = "auto"` is configured, use `async def test_*`:

```python
import pytest

async def test_transcribe_success():
    """Test voice transcription with valid audio."""
    audio_bytes = b"fake_audio_data"
    result = await transcribe(audio_bytes)
    assert result is not None
    assert isinstance(result, str)

async def test_transcribe_missing_key():
    """Transcribe returns None when STT_API_KEY not set."""
    # Would need to mock os.environ
    result = await transcribe(b"audio")
    assert result is None
```

**Async context managers:**

```python
async def test_typing_loop():
    """Test _typing_loop cancels task on exit."""
    async with _typing_loop(chat_mock) as _:
        pass
    # Task should be cancelled
```

## Mocking

**Framework:** pytest with `unittest.mock` (standard library)

**Patterns (to follow when tests are written):**

```python
from unittest.mock import Mock, AsyncMock, patch

async def test_send_status():
    """_send_status sends reply to message."""
    update = Mock()
    update.message.reply_text = AsyncMock(return_value=Mock(id=123))
    
    result = await _send_status(update, "Test text")
    
    update.message.reply_text.assert_called_once_with("Test text", do_quote=True)
    assert result.id == 123

@patch("bot.features.audio.STT_API_KEY", "test_key")
@patch("httpx.AsyncClient.post")
async def test_transcribe_api_call(mock_post):
    """Transcribe makes correct Whisper API request."""
    mock_post.return_value = Mock(status_code=200)
    mock_post.return_value.json.return_value = {"text": "hello world"}
    
    result = await transcribe(b"audio")
    
    assert result == "hello world"
    mock_post.assert_called_once()
```

**What to Mock:**
- External API calls (Telegram, Claude SDK, Groq, Gemini, OpenAI)
- `os.environ` for config testing
- `Path.read_text()` / `Path.write_text()` for file operations
- Async operations in unit tests

**What NOT to Mock:**
- Core logic (parsing, chunking, formatting)
- Pure functions without side effects
- Integration tests should use real file I/O for `/data`

## Test Data and Fixtures

**Fixtures (to be added in conftest.py):**

```python
import pytest
from pathlib import Path
import tempfile

@pytest.fixture
def temp_data_dir():
    """Temporary /data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
async def mock_update():
    """Mock Telegram Update object."""
    from unittest.mock import Mock, AsyncMock
    update = Mock()
    update.message = Mock()
    update.message.reply_text = AsyncMock(return_value=Mock(id=123))
    update.message.chat = Mock()
    return update

@pytest.fixture
def sample_markdown():
    """Sample markdown for parsing tests."""
    return """# Header
Some text here.

## Subheader
More content."""
```

**Location:**
- Fixtures: `tests/conftest.py`
- Factory functions: `tests/factories.py` for creating test objects

## Test Types

**Unit Tests:**
- Scope: Single function or class method
- Approach: Mock external dependencies, test pure logic
- Examples to write:
  - `test_chunk_markdown()` - test markdown splitting logic
  - `test_build_core_context()` - test context assembly with fake files
  - `test_build_options()` - test SDK options building

**Integration Tests:**
- Scope: Multiple modules working together
- Approach: Real file I/O, real async operations, minimal mocking
- Examples to write:
  - `test_memory_flow()` - read SOUL.md, build context, inject into options
  - `test_telegram_message_flow()` - message → Claude → response update

**E2E Tests:**
- Not used (would require running Docker containers)
- Manual testing via `/m bot` or dashboard sufficient

## Coverage

**Requirements:** None explicitly enforced in `pyproject.toml`

**View Coverage:**
```bash
python -m pytest tests/ --cov=bot --cov-report=html
# Open htmlcov/index.html
```

**Target:** Aim for >80% on critical paths (memory, bridge, query building)

## Error Testing

**Pattern for testing error paths:**

```python
async def test_transcribe_api_error():
    """Transcribe returns None on API error."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = Exception("Connection failed")
        result = await transcribe(b"audio")
        assert result is None

async def test_transcribe_no_text_in_response():
    """Transcribe returns None when API has no text."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"text": ""}  # Empty
        result = await transcribe(b"audio")
        assert result is None

def test_build_options_missing_file():
    """build_options handles missing SOUL.md gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        opts = build_options(data_dir=Path(tmpdir))
        # Should not raise, system_prompt just empty
        assert isinstance(opts, ClaudeCodeOptions)
```

## Debugging Tests

**Run single test:**
```bash
python -m pytest tests/test_memory.py::test_chunk_markdown -v
```

**Show print statements:**
```bash
python -m pytest tests/ -v -s
```

**Drop into debugger on failure:**
```bash
python -m pytest tests/ -v --pdb
```

**Run only tests marked as slow:**
```bash
python -m pytest tests/ -v -m slow
```

---

*Testing analysis: 2026-04-13*
