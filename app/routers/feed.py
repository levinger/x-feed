from typing import Optional

from fastapi import APIRouter, Query

from app.database import get_feed, get_all_keywords
from app.config import settings

router = APIRouter(tags=["feed"])


@router.get("/feed")
async def read_feed(
    keyword: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    before: Optional[str] = Query(None),
    verified_only: bool = Query(False),
):
    tweets = get_feed(keyword=keyword, limit=limit, offset=offset, before=before, verified_only=verified_only)
    # Return full keyword objects so frontend has IDs for deletion
    keywords = get_all_keywords()
    return {
        "tweets":   tweets,
        "keywords": keywords,
        "has_more": len(tweets) == limit,
    }
