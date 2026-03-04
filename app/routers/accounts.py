from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scraper import add_account, get_accounts, delete_account

router = APIRouter(tags=["accounts"])


class AccountIn(BaseModel):
    username: str
    password: str
    email: str
    email_password: str
    cookies: Optional[str] = None


@router.get("/accounts")
async def list_accounts():
    return await get_accounts()


@router.post("/accounts", status_code=201)
async def create_account(body: AccountIn):
    try:
        await add_account(
            username=body.username,
            password=body.password,
            email=body.email,
            email_password=body.email_password,
            cookies=body.cookies,
        )
        return {"status": "added", "username": body.username}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.delete("/accounts/{username}", status_code=204)
async def remove_account(username: str):
    await delete_account(username)
