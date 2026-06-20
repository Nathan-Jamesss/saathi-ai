"""RAG layer — ChromaDB retrieval from NCERT corpus"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)

_chroma_client = None
_collection    = None
_ready         = False


def init_chroma():
    global _chroma_client, _collection, _ready
    try:
        import chromadb
        persist_dir = os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma")
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
        try:
            _collection = _chroma_client.get_collection("ncert_corpus")
            count = _collection.count()
            logger.info(f"ChromaDB loaded: {count} chunks in ncert_corpus")
            _ready = count > 0
        except Exception:
            logger.info("ChromaDB: ncert_corpus not found. Run build_index.py to populate.")
            _ready = False
    except Exception as e:
        logger.warning(f"ChromaDB init failed: {e}. RAG disabled.")
        _ready = False


def is_chroma_ready() -> bool:
    return _ready


def retrieve_chunks(query: str, grade: int, subject: str, n_results: int = 5) -> List[str]:
    if not _ready or _collection is None:
        return []
    try:
        from google.genai import types
        from core.keys import embed_content

        result = embed_content(
            model="models/gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        query_embedding = result.embeddings[0].values

        try:
            res = _collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"$and": [{"class": grade}, {"subject": subject}]},
            )
        except Exception:
            res = _collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"subject": subject},
            )

        return [d for d in res.get("documents", [[]])[0] if d]
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return []


def get_collection():
    return _collection


def get_client():
    return _chroma_client
