"""
build_index.py — Chunk NCERT texts, embed with text-embedding-004, store in ChromaDB.

Usage:
    python scripts/build_index.py           # full index
    python scripts/build_index.py --limit 200  # 200 items per subject (fast demo)
"""

import os
import sys
import json
import time
import glob
import logging
import argparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "ncert")
CHUNK_SIZE = 500
OVERLAP    = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i: i + chunk_size]))
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]


def embed_batch(texts: list, api_key: str) -> list:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    embeddings = []
    for text in texts:
        try:
            result = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings.append(result.embeddings[0].values)
        except Exception as e:
            logger.warning(f"Embedding failed: {e}. Retrying in 5s...")
            time.sleep(5)
            try:
                result = client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=text,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                embeddings.append(result.embeddings[0].values)
            except Exception:
                embeddings.append(None)
        time.sleep(0.05)
    return embeddings


def build_index(limit_per_subject: int = 0):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not set.")
        sys.exit(1)

    persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")
    os.makedirs(persist_dir, exist_ok=True)

    import chromadb
    client = chromadb.PersistentClient(path=persist_dir)

    try:
        client.delete_collection("ncert_corpus")
        logger.info("Deleted existing ncert_corpus")
    except Exception:
        pass

    collection = client.create_collection(
        name="ncert_corpus",
        metadata={"hnsw:space": "cosine"},
    )

    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not json_files:
        logger.warning(f"No JSON files in {DATA_DIR}. Run download_ncert.py first.")
        sys.exit(1)

    logger.info(f"Found {len(json_files)} subject files")
    if limit_per_subject:
        logger.info(f"Limiting to {limit_per_subject} items per subject (demo mode)")

    total_chunks = 0
    batch_docs, batch_ids, batch_metas = [], [], []
    BATCH_SIZE = 50

    for fpath in json_files:
        with open(fpath, encoding="utf-8") as f:
            items = json.load(f)

        if limit_per_subject:
            items = items[:limit_per_subject]

        for item in items:
            text    = item.get("text", "") or item.get("content", "")
            cls     = item.get("class", 0)
            subject = item.get("subject", "").lower().strip()
            chapter = item.get("chapter", "")

            if not text.strip():
                continue

            for ci, chunk in enumerate(chunk_text(text)):
                doc_id = f"{cls}_{subject}_{chapter[:20]}_{ci}_{total_chunks}".replace(" ", "_")
                batch_docs.append(chunk)
                batch_ids.append(doc_id)
                batch_metas.append({"class": int(cls) if cls else 0, "subject": subject, "chapter": chapter})
                total_chunks += 1

                if len(batch_docs) >= BATCH_SIZE:
                    _flush_batch(collection, batch_docs, batch_ids, batch_metas, api_key)
                    batch_docs, batch_ids, batch_metas = [], [], []

    if batch_docs:
        _flush_batch(collection, batch_docs, batch_ids, batch_metas, api_key)

    logger.info(f"Done: {total_chunks} chunks indexed in ChromaDB at {persist_dir}")


def _flush_batch(collection, docs, ids, metas, api_key):
    logger.info(f"Embedding {len(docs)} chunks...")
    embeddings = embed_batch(docs, api_key)
    valid = [(d, i, m, e) for d, i, m, e in zip(docs, ids, metas, embeddings) if e is not None]
    if valid:
        d, i, m, e = zip(*valid)
        collection.add(documents=list(d), ids=list(i), metadatas=list(m), embeddings=list(e))
    logger.info(f"  Stored {len(valid)} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max items per subject (0 = all)")
    args = parser.parse_args()
    build_index(limit_per_subject=args.limit)
