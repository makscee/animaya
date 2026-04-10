"""Semantic search over Markdown files using sidecar embeddings.

No database — embeddings stored as JSON files alongside .md files.

Usage:
  python -m bot.memory.search "what do I like to eat"
  python -m bot.memory.search --index
  python -m bot.memory.search --index path.md
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import sys
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_data_dir = Path(os.environ.get("DATA_PATH", "/data"))

EMBEDDING_BASE_URL = os.environ.get("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
EMBEDDING_API_KEY = os.environ.get("EMBEDDING_API_KEY", os.environ.get("LLM_API_KEY", ""))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")


def chunk_markdown(content: str, max_chars: int = 500) -> list[dict]:
    """Split markdown into chunks by paragraphs/headers."""
    if not content.strip():
        return []

    blocks = []
    current = []
    for line in content.split("\n"):
        if line.startswith("#") and current:
            blocks.append("\n".join(current))
            current = [line]
        elif line.strip() == "" and current:
            blocks.append("\n".join(current))
            current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))

    chunks = []
    buffer = ""
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(buffer) + len(block) < max_chars:
            buffer = (buffer + "\n\n" + block).strip()
        else:
            if buffer:
                chunks.append(buffer)
            if len(block) > max_chars:
                for i in range(0, len(block), max_chars):
                    chunks.append(block[i : i + max_chars])
                buffer = ""
            else:
                buffer = block
    if buffer:
        chunks.append(buffer)

    return [{"text": c, "hash": hashlib.md5(c.encode()).hexdigest()[:12]} for c in chunks if c.strip()]


def _embed_batch(texts: list[str]) -> list[list[float]]:
    if not EMBEDDING_API_KEY:
        raise ValueError("No EMBEDDING_API_KEY set")

    resp = httpx.post(
        f"{EMBEDDING_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {EMBEDDING_API_KEY}"},
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    embeddings = sorted(data["data"], key=lambda x: x["index"])
    return [e["embedding"] for e in embeddings]


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


def _sidecar_path(file_path: Path) -> Path:
    return file_path.parent / f".{file_path.name}.embeddings.json"


_SKIP_FILES = {"CLAUDE.md", "BOOTSTRAP.md", "bot.Dockerfile", "config.json"}


def index_file(file_path: Path) -> int:
    """Index a single file, creating/updating its sidecar. Returns chunk count."""
    if not file_path.exists() or file_path.is_dir():
        return 0

    content = file_path.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_markdown(content)
    if not chunks:
        return 0

    sidecar = _sidecar_path(file_path)
    file_hash = hashlib.md5(content.encode()).hexdigest()[:16]

    old_chunks = {}
    if sidecar.exists():
        try:
            old_data = json.loads(sidecar.read_text(encoding="utf-8"))
            if old_data.get("file_hash") == file_hash:
                return len(old_data.get("chunks", []))
            for c in old_data.get("chunks", []):
                old_chunks[c["hash"]] = c.get("embedding")
        except Exception:
            pass

    to_embed = []
    to_embed_indices = []
    for i, chunk in enumerate(chunks):
        if chunk["hash"] in old_chunks and old_chunks[chunk["hash"]]:
            chunk["embedding"] = old_chunks[chunk["hash"]]
        else:
            to_embed.append(chunk["text"])
            to_embed_indices.append(i)

    if to_embed:
        try:
            vectors = _embed_batch(to_embed)
            for idx, vec in zip(to_embed_indices, vectors):
                chunks[idx]["embedding"] = _normalize(vec)
        except Exception as e:
            logger.warning("Embedding failed for %s: %s", file_path.name, e)
            return 0

    sidecar_data = {
        "file": str(file_path.name),
        "file_hash": file_hash,
        "model": EMBEDDING_MODEL,
        "chunks": [
            {"text": c["text"], "hash": c["hash"], "embedding": c["embedding"]}
            for c in chunks
            if "embedding" in c
        ],
    }
    sidecar.write_text(json.dumps(sidecar_data), encoding="utf-8")
    return len(sidecar_data["chunks"])


def index_directory(dir_path: Path) -> int:
    """Index all .md files recursively. Returns total chunks."""
    total = 0
    for md_file in sorted(dir_path.rglob("*.md")):
        if md_file.name.startswith(".") or md_file.name.startswith("_"):
            continue
        if md_file.name in _SKIP_FILES:
            continue
        try:
            n = index_file(md_file)
            if n > 0:
                logger.info("Indexed %s: %d chunks", md_file.relative_to(dir_path), n)
            total += n
        except Exception:
            logger.warning("Failed to index %s", md_file, exc_info=True)
    return total


def search(query_text: str, search_dirs: list[Path] | None = None, top_k: int = 10) -> list[dict]:
    """Search sidecar files for chunks similar to query. Returns [{text, file, score}]."""
    dirs = search_dirs or [_data_dir / "memory", _data_dir / "spaces", _data_dir]

    try:
        query_vec = _normalize(_embed_batch([query_text])[0])
    except Exception as e:
        logger.warning("Query embedding failed: %s", e)
        return []

    results = []
    for dir_path in dirs:
        if not dir_path.exists():
            continue
        for sidecar_file in dir_path.rglob(".*.embeddings.json"):
            try:
                data = json.loads(sidecar_file.read_text(encoding="utf-8"))
                source_file = data.get("file", sidecar_file.name)
                rel_dir = str(sidecar_file.parent.relative_to(_data_dir))
                for chunk in data.get("chunks", []):
                    embedding = chunk.get("embedding")
                    if not embedding:
                        continue
                    score = sum(a * b for a, b in zip(query_vec, embedding))
                    results.append({
                        "text": chunk["text"],
                        "file": f"{rel_dir}/{source_file}" if rel_dir != "." else source_file,
                        "score": round(score, 4),
                    })
            except Exception:
                continue

    seen = {}
    for r in results:
        key = r["text"][:100]
        if key not in seen or r["score"] > seen[key]["score"]:
            seen[key] = r
    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:top_k]


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m bot.memory.search 'query'")
        print("  python -m bot.memory.search --index")
        print("  python -m bot.memory.search --index file.md")
        sys.exit(1)

    if sys.argv[1] == "--index":
        if len(sys.argv) > 2:
            n = index_file(Path(sys.argv[2]))
            print(f"Indexed: {n} chunks")
        else:
            total = 0
            for d in ("memory", "spaces"):
                dir_path = _data_dir / d
                if dir_path.exists():
                    n = index_directory(dir_path)
                    total += n
                    print(f"Indexed {d}/: {n} chunks")
            for f in _data_dir.glob("*.md"):
                if not f.name.startswith(".") and f.name not in _SKIP_FILES:
                    total += index_file(f)
            print(f"Total: {total} chunks")
    else:
        results = search(" ".join(sys.argv[1:]))
        if not results:
            print("No results. Run --index first.")
        else:
            for r in results:
                print(f"\n[{r['score']:.3f}] {r['file']}:")
                print(f"  {r['text'][:200]}")


if __name__ == "__main__":
    main()
