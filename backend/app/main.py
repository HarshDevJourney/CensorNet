from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.routes import chunk_router, job_router, video_router

app = FastAPI(title="Video Censorship")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router)
app.include_router(job_router)
app.include_router(chunk_router)


@app.on_event("startup")
def create_tables():
    # dev convenience; switch to Alembic migrations once the schema settles
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"ok": True}