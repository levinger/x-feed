import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import add_keyword, delete_keyword, get_all_keywords
from app.scheduler import fetch_all_keywords

router = APIRouter(tags=["keywords"])


class KeywordIn(BaseModel):
    keyword: str


@router.get("/keywords")
async def list_keywords():
    return get_all_keywords()


@router.post("/keywords", status_code=201)
async def create_keyword(body: KeywordIn):
    if not body.keyword.strip():
        raise HTTPException(400, "Keyword cannot be empty")
    kw = add_keyword(body.keyword)
    asyncio.create_task(fetch_all_keywords())
    return kw


@router.delete("/keywords/{keyword_id}", status_code=204)
async def remove_keyword(keyword_id: int):
    delete_keyword(keyword_id)
