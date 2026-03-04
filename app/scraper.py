import json
import logging
import re
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_api = None


def _patch_twscrape():
    """
    twscrape 0.17.0 bug: X's JS bundle uses unquoted object keys in some entries
    (valid JS, invalid JSON). Patch get_scripts_list to handle this.
    Applied at import time so it survives pip reinstalls.
    """
    try:
        import twscrape.xclid as _xclid

        def _patched_get_scripts_list(text: str):
            from twscrape.xclid import script_url
            scripts = text.split('e=>e+"."+')[1].split('[e]+"a.js"')[0].lstrip("+")
            fixed = re.sub(r'([{,])\s*([A-Za-z_$][A-Za-z0-9_$/@.-]*)\s*:', r'\1"\2":', scripts)
            try:
                for k, v in json.loads(fixed).items():
                    yield script_url(k, f"{v}a")
            except json.decoder.JSONDecodeError as e:
                raise Exception("Failed to parse scripts") from e

        _xclid.get_scripts_list = _patched_get_scripts_list
    except Exception as e:
        logger.warning(f"[scraper] Could not patch twscrape xclid: {e}")


_patch_twscrape()


def get_api():
    global _api
    if _api is None:
        from twscrape import API
        from twscrape.logger import set_log_level
        _api = API(settings.get_accounts_db_path())
        set_log_level("WARNING")
    return _api


async def search_keyword(keyword: str, limit: int = 50) -> list[dict]:
    api = get_api()
    results = []
    try:
        async for tweet in api.search(keyword, limit=limit):
            results.append(_normalize(tweet, keyword))
    except Exception as e:
        logger.error(f"[scraper] Error searching '{keyword}': {e}")
    return results


def _normalize(tweet, keyword: str) -> dict:
    return {
        "tweet_id":        str(tweet.id),
        "keyword":         keyword,
        "content":         tweet.rawContent,
        "author_username": tweet.user.username,
        "author_name":     tweet.user.displayname,
        "author_avatar":   tweet.user.profileImageUrl,
        "tweet_url":       tweet.url,
        "like_count":      tweet.likeCount,
        "retweet_count":   tweet.retweetCount,
        "reply_count":     tweet.replyCount,
        "tweeted_at":      tweet.date.isoformat(),
    }


async def add_account(
    username: str,
    password: str,
    email: str,
    email_password: str,
    cookies: Optional[str] = None,
) -> bool:
    api = get_api()
    await api.pool.add_account(
        username, password, email, email_password,
        cookies=cookies,
    )
    if cookies:
        from app.database import save_account_credentials
        save_account_credentials(username, cookies)
    else:
        await api.pool.login_all()
    return True


async def restore_accounts():
    """Re-register accounts from our DB into twscrape on startup."""
    from app.database import get_stored_accounts
    accounts = get_stored_accounts()
    if not accounts:
        return
    api = get_api()
    restored = 0
    for acc in accounts:
        try:
            await api.pool.add_account(
                acc["username"], "", "", "",
                cookies=acc["cookies"],
            )
            restored += 1
        except Exception:
            pass  # "already exists" is expected — not fatal
    logger.info(f"[scraper] Restored {restored} account(s) from DB.")


async def get_accounts() -> list[dict]:
    api = get_api()
    accounts = await api.pool.get_all()
    return [
        {
            "username":  a.username,
            "active":    a.active,
            "last_used": str(a.last_used) if a.last_used else None,
            "error_msg": a.error_msg,
        }
        for a in accounts
    ]


async def delete_account(username: str):
    import aiosqlite
    async with aiosqlite.connect(settings.get_accounts_db_path()) as db:
        await db.execute("DELETE FROM accounts WHERE username = ?", (username,))
        await db.commit()
    from app.database import delete_account_credentials
    delete_account_credentials(username)
    global _api
    _api = None
