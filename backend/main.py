from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.v1.api import router as api_router
from database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from config import settings

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Initial System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)

app.include_router(api_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)