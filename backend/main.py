import os, re, uuid, shutil, threading, time, zipfile
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import yt_dlp

APP_DIR = Path(os.getenv("JOB_DIR", "/tmp/playlist-jobs"))
APP_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
MAX_ITEMS = int(os.getenv("MAX_PLAYLIST_ITEMS", "100"))
JOBS = {}
LOCK = threading.Lock()
POOL = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="Playlist Downloader API", version="1.0.0")
origins = [x.strip() for x in os.getenv("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET","POST"], allow_headers=["*"])

class PlaylistRequest(BaseModel):
    url: str
    limit: int = Field(default=50, ge=1, le=100)

class JobRequest(BaseModel):
    url: str
    indices: list[int] = Field(min_length=1, max_length=100)
    quality: int = Field(default=192)

def validate_url(url: str):
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        if p.scheme not in ("http", "https") or host not in ALLOWED_HOSTS:
            raise ValueError()
        if not (host.endswith("youtube.com") or host == "youtu.be"):
            raise ValueError()
    except Exception:
        raise HTTPException(400, "Informe um link válido do YouTube.")
    return url

def ydl_base():
    return {"quiet": True, "no_warnings": True, "ignoreerrors": True, "extract_flat": True, "skip_download": True, "noplaylist": False}

@app.get("/health")
def health():
    return {"ok": True, "service": "playlist-downloader-api"}

@app.post("/api/playlist")
def playlist(req: PlaylistRequest):
    url = validate_url(req.url)
    try:
        with yt_dlp.YoutubeDL(ydl_base()) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info: raise ValueError("Não foi possível ler a playlist.")
        entries = []
        for n, e in enumerate((info.get("entries") or [])[:req.limit], start=1):
            if not e: continue
            entries.append({"index": int(e.get("playlist_index") or n), "title": e.get("title") or "Vídeo sem título", "duration": e.get("duration"), "thumbnail": e.get("thumbnail") or ""})
        if not entries: raise ValueError("Nenhum vídeo disponível foi encontrado.")
        return {"title": info.get("title") or "Playlist", "entries": entries, "total_returned": len(entries)}
    except Exception as e:
        raise HTTPException(422, str(e)[:300])

def run_job(job_id, url, indices, quality):
    job = JOBS[job_id]
    work = APP_DIR / job_id
    work.mkdir(parents=True, exist_ok=True)
    try:
        job.update(status="working", progress=2, message="Preparando os downloads…")
        # playlist_items uses playlist positions; selected indexes are positions in the playlist
        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(work / "%(playlist_index)03d - %(title).180B.%(ext)s"),
            "ignoreerrors": True, "noplaylist": False, "quiet": True, "no_warnings": True,
            "playlist_items": ",".join(str(i) for i in sorted(set(indices))),
            "postprocessors": [{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":str(quality)}],
            "progress_hooks": [lambda d: job.update(message=("Baixando: " + str(d.get("filename",""))[-90:]) if d.get("status")=="downloading" else "Convertendo áudio…")],
            "retries": 2, "fragment_retries": 2, "windowsfilenames": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        mp3s = sorted(work.glob("*.mp3"))
        if not mp3s: raise RuntimeError("Nenhum MP3 foi gerado. Verifique a autorização, disponibilidade e compatibilidade dos vídeos.")
        job.update(progress=88, message="Compactando os arquivos em ZIP…")
        zip_path = work / "playlist-mp3.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in mp3s: z.write(f, f.name)
        job.update(status="done", progress=100, message=f"Concluído: {len(mp3s)} arquivo(s) MP3.", zip=str(zip_path), count=len(mp3s))
    except Exception as e:
        job.update(status="error", progress=0, message=str(e)[:300])
    finally:
        job["updated"] = time.time()

@app.post("/api/jobs")
def create_job(req: JobRequest):
    url = validate_url(req.url)
    if req.quality not in (128,192,320): raise HTTPException(400, "Qualidade deve ser 128, 192 ou 320 kbps.")
    if len(set(req.indices)) != len(req.indices) or any(i < 1 or i > MAX_ITEMS for i in req.indices):
        raise HTTPException(400, f"Seleção inválida. Limite: {MAX_ITEMS} faixas.")
    job_id = uuid.uuid4().hex
    with LOCK:
        # Basic in-memory cap to reduce accidental overload on this demo service
        active = sum(1 for j in JOBS.values() if j.get("status") in ("queued","working"))
        if active >= 2: raise HTTPException(429, "O servidor está ocupado. Tente novamente em alguns minutos.")
        JOBS[job_id] = {"status":"queued","progress":0,"message":"Na fila…","created":time.time(),"updated":time.time()}
    POOL.submit(run_job, job_id, url, req.indices, req.quality)
    return {"job_id": job_id}

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Tarefa não encontrada ou expirada.")
    return {k:v for k,v in job.items() if k not in ("zip",)}

@app.get("/api/jobs/{job_id}/download")
def download(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "done" or not job.get("zip"):
        raise HTTPException(404, "O ZIP ainda não está pronto.")
    p = Path(job["zip"])
    if not p.exists(): raise HTTPException(404, "Arquivo expirado.")
    return FileResponse(p, media_type="application/zip", filename="playlist-mp3.zip")
