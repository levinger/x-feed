import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database import get_active_keywords, upsert_tweets, log_fetch
from app.scraper import search_keyword

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def fetch_all_keywords():
    try:
        keywords = get_active_keywords()
        if not keywords:
            logger.info("[scheduler] No active keywords, skipping.")
            return

        logger.info(f"[scheduler] Fetching {len(keywords)} keyword(s).")
        for keyword in keywords:
            try:
                logger.info(f"[scheduler] Searching '{keyword}'...")
                tweets = await search_keyword(keyword, limit=settings.TWEETS_PER_KEYWORD)
                new_count = upsert_tweets(tweets)
                log_fetch(keyword, new_count)
                logger.info(f"[scheduler] '{keyword}': {new_count} new tweet(s).")
            except Exception as e:
                log_fetch(keyword, 0, error=str(e))
                logger.error(f"[scheduler] '{keyword}' failed: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"[scheduler] fetch_all_keywords crashed: {e}", exc_info=True)


def start_scheduler():
    scheduler.add_job(
        fetch_all_keywords,
        trigger=IntervalTrigger(minutes=settings.FETCH_INTERVAL_MINUTES),
        id="fetch_keywords",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(f"[scheduler] Started. Interval: {settings.FETCH_INTERVAL_MINUTES}m.")


def stop_scheduler():
    scheduler.shutdown(wait=False)
