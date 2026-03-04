import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from app.config import settings

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS keywords (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword    TEXT NOT NULL UNIQUE,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tweets (
    tweet_id        TEXT PRIMARY KEY,
    keyword         TEXT NOT NULL,
    content         TEXT NOT NULL,
    author_username TEXT NOT NULL,
    author_name     TEXT NOT NULL,
    author_avatar   TEXT,
    tweet_url       TEXT NOT NULL,
    like_count      INTEGER NOT NULL DEFAULT 0,
    retweet_count   INTEGER NOT NULL DEFAULT 0,
    reply_count     INTEGER NOT NULL DEFAULT 0,
    tweeted_at      TEXT NOT NULL,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tweets_tweeted_at ON tweets(tweeted_at DESC);
CREATE INDEX IF NOT EXISTS idx_tweets_keyword    ON tweets(keyword);

CREATE TABLE IF NOT EXISTS fetch_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword    TEXT NOT NULL,
    tweets_new INTEGER NOT NULL DEFAULT 0,
    ran_at     TEXT NOT NULL DEFAULT (datetime('now')),
    error      TEXT
);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(settings.get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(DDL)
        conn.execute(
            "DELETE FROM tweets WHERE keyword NOT IN (SELECT keyword FROM keywords)"
        )


# --- Keywords ---

def get_active_keywords() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT keyword FROM keywords WHERE active = 1 ORDER BY created_at"
        ).fetchall()
        return [r["keyword"] for r in rows]


def get_all_keywords() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, keyword, active, created_at FROM keywords ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def add_keyword(keyword: str) -> dict:
    kw = keyword.strip().lower()
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (kw,))
        row = conn.execute(
            "SELECT id, keyword, active, created_at FROM keywords WHERE keyword = ?", (kw,)
        ).fetchone()
        return dict(row)


def delete_keyword(keyword_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT keyword FROM keywords WHERE id = ?", (keyword_id,)).fetchone()
        if row:
            conn.execute("DELETE FROM tweets WHERE keyword = ?", (row["keyword"],))
        conn.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))


# --- Tweets ---

def upsert_tweets(tweets: list[dict]) -> int:
    new_count = 0
    with get_connection() as conn:
        for t in tweets:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO tweets
                  (tweet_id, keyword, content, author_username, author_name,
                   author_avatar, tweet_url, like_count, retweet_count, reply_count, tweeted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    t["tweet_id"], t["keyword"], t["content"],
                    t["author_username"], t["author_name"], t["author_avatar"],
                    t["tweet_url"], t["like_count"], t["retweet_count"],
                    t["reply_count"], t["tweeted_at"],
                ),
            )
            new_count += cur.rowcount
    return new_count


def get_feed(
    keyword: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    before: Optional[str] = None,
) -> list[dict]:
    query = "SELECT * FROM tweets WHERE 1=1"
    params: list = []
    if keyword:
        query += " AND keyword = ?"
        params.append(keyword)
    if before:
        query += " AND tweeted_at < ?"
        params.append(before)
    query += " ORDER BY tweeted_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- Fetch log ---

def log_fetch(keyword: str, tweets_new: int, error: Optional[str] = None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO fetch_log (keyword, tweets_new, error) VALUES (?,?,?)",
            (keyword, tweets_new, error),
        )
