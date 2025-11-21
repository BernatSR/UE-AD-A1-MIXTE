from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

try:
    from pymongo import MongoClient
except ImportError:
    print("pymongo not installed. Install with: pip install pymongo", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent

DATA_SOURCES = [
    {
        "path": ROOT / "movie" / "data" / "movies.json",
        "key": "movies",
        "collection": "movies",
        "id_field": "id",
    },
    {
        "path": ROOT / "movie" / "data" / "actors.json",
        "key": "actors",
        "collection": "actors",
        "id_field": "id",
    },
    {
        "path": ROOT / "user" / "data" / "users.json",
        "key": "users",
        "collection": "users",
        "id_field": "id",
    },
    {
        "path": ROOT / "booking" / "data" / "bookings.json",
        "key": "bookings",
        "collection": "bookings",
        "id_field": "userid",
    },
    {
        "path": ROOT / "schedule" / "data" / "times.json",
        "key": "schedule",
        "collection": "schedule",
        "id_field": "date",
    },
]


def load_json(path: Path, key: str) -> List[Dict[str, Any]]:
    if not path.exists():
        print(f"[warn] Missing file: {path}")
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        val = raw.get(key, [])
        if isinstance(val, list):
            return val
        print(f"[warn] Key '{key}' not a list in {path}; skipping")
        return []
    except Exception as e:
        print(f"[warn] Failed reading {path}: {e}")
        return []


def append_mode(collection, docs: List[Dict[str, Any]], id_field: str) -> int:
    if not docs:
        return 0
    existing_ids = set()
    try:
        existing_ids = {d.get(id_field) for d in collection.find({}, {id_field: 1, "_id": 0})}
    except Exception:
        pass
    to_insert = [d for d in docs if d.get(id_field) not in existing_ids]
    if not to_insert:
        return 0
    collection.insert_many([d.copy() for d in to_insert])
    return len(to_insert)


def replace_mode(collection, docs: List[Dict[str, Any]]) -> int:
    collection.delete_many({})
    if not docs:
        return 0
    collection.insert_many([d.copy() for d in docs])
    return len(docs)


def import_all(mongo_url: str, db_name: str, replace: bool) -> None:
    client = MongoClient(mongo_url)
    db = client[db_name]
    total = 0
    for src in DATA_SOURCES:
        docs = load_json(src["path"], src["key"])
        collection = db[src["collection"]]
        if replace:
            inserted = replace_mode(collection, docs)
            mode = "replaced"
        else:
            inserted = append_mode(collection, docs, src["id_field"])
            mode = "appended"
        total += inserted
        print(f"[{src['collection']}] {mode} {inserted} docs (source: {src['path'].name})")
    print(f"Done. Inserted {total} documents.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Import JSON data into MongoDB.")
    p.add_argument("--mongo-url", default=os.environ.get("MONGO_URL", "mongodb://root:example@localhost:27017/?authSource=admin"), help="Mongo connection URL")
    p.add_argument("--db-name", default=os.environ.get("MONGO_DB_NAME", "appdb"), help="Database name")
    p.add_argument("--replace", action="store_true", help="Drop collections and fully reload")
    return p.parse_args()


def main():
    args = parse_args()
    try:
        import_all(args.mongo_url, args.db_name, args.replace)
    except Exception as e:
        print(f"[error] Import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()