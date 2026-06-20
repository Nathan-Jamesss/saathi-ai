"""Saathi.AI — FastAPI backend entrypoint"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()  # loads .env when running locally; Render uses its own env vars
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.health  import router as health_router
from api.process import router as process_router
from api.tts     import router as tts_router
from api.export  import router as export_router
from core.rag    import init_chroma


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize ChromaDB on startup."""
    init_chroma()
    yield


app = FastAPI(title="Saathi.AI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # demo: any frontend origin (Vercel, localhost)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router,  prefix="/api")
app.include_router(process_router, prefix="/api")
app.include_router(tts_router,     prefix="/api")
app.include_router(export_router,  prefix="/api")


@app.get("/")
def root():
    return {"service": "Saathi.AI", "status": "running"}
