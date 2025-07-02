from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from api.v1.api import router as api_router
from config import settings

import os
from dotenv import load_dotenv
import asyncpg
import asyncio
import ssl
import boto3
from botocore.exceptions import ClientError
import uuid

# Load environment variables
load_dotenv()

# Initialize DB and S3
Base.metadata.create_all(bind=engine)

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Create app
app = FastAPI(title="Portfolionew003 API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# DB connection function
async def connect_db():
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        conn = await asyncpg.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            ssl=ssl_context
        )           
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None

# ========== ROUTES ==========

@app.get("/health", tags=["Health"])
async def health_check():
    return JSONResponse(content={"status": "ok"}, status_code=200)

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "🚀 Deployment Successful!",
        "status": "running",
        "timestamp": asyncio.get_event_loop().time(),
        "origin": os.getenv("FRONTEND_DOMAIN")
    }

@app.get("/api/hello", tags=["API"])
async def api_hello():
    return {"message": "Hello from the backend!"}

@app.get("/api/data", tags=["Database"])
async def get_data():
    try:
        conn = await connect_db()
        if not conn:
            return {"error": "Database connection failed"}
        row = await conn.fetchrow("SELECT NOW() as current_time")
        await conn.close()
        return {"Date": row["current_time"], "message": "Hello from the database!"}
    except Exception as e:
        return {"error": f"Server error: {e}"}

@app.get("/api/debug-env", tags=["Debug"])
async def debug_env():
    return {
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "AWS_REGION": os.getenv("AWS_REGION"),
        "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "FRONTEND_DOMAIN": os.getenv("FRONTEND_DOMAIN"),
    }

@app.post("/api/upload", tags=["File Handling"])
async def upload_file(file: UploadFile = File(...)):
    try:
        ext = file.filename.split(".")[-1]
        unique_filename = f"images/{uuid.uuid4()}.{ext}"
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        file_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{unique_filename}"
        return {
            "message": "File uploaded successfully",
            "filename": unique_filename,
            "file_url": file_url,
            "content_type": file.content_type,
            "size": file.size
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

@app.get("/api/list-images", tags=["File Handling"])
async def list_images():
    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME)
        images = [obj['Key'] for obj in response.get('Contents', [])]
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list images: {e}")

@app.get("/api/generate-presigned-url", tags=["File Handling"])
async def get_presigned_url(filename: str):
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': filename},
            ExpiresIn=3600
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presigned URL generation failed: {e}")

# Include other routers (like user/auth etc.)
app.include_router(api_router, prefix="/v1")

# Run locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
