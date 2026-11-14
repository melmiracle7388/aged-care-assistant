"""Step 2: cut the documents into sections and store them in Chroma.

Run once (and again whenever the files in data/ change):   python ingest.py
The first run downloads a small embedding model (about 80 MB), so it needs internet.
"""
import shutil

import chromadb

import config
from chunker import load_chunks


def main():
    chunks = load_chunks()
    if config.DB_PATH.exists():
        shutil.rmtree(config.DB_PATH)  # rebuild from scratch so nothing old is left behind
    db = chromadb.PersistentClient(path=str(config.DB_PATH))
    col = db.create_collection(config.COLLECTION)
    col.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["meta"] for c in chunks],
    )
    residents = sum(1 for c in chunks if c["meta"]["doc_type"] == "resident")
    policies = len(chunks) - residents
    print(f"Stored {len(chunks)} sections in Chroma ({residents} resident, {policies} policy).")


if __name__ == "__main__":
    main()
