# backend/api/v1/api.py
from fastapi import APIRouter
from api.v1.endpoints import auth

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])