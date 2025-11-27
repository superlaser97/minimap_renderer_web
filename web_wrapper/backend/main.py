import os
import uuid
import shutil
import asyncio
import logging
import subprocess
import sys
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Response, Cookie, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import aiofiles
from typing import Optional
import httpx
import database

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
RENDERER_ROOT = Path("../../minimap_renderer/src").resolve() # Pointing to the src directory where render.py lives

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: Optional[str] = ""

# Worker Queue
queue = asyncio.Queue()

async def worker():
    while True:
        job_id = await queue.get()
        job = database.get_job(job_id)
        
        if not job:
            queue.task_done()
            continue
            
        try:
            database.update_job_status(job_id, JobStatus.PROCESSING)
            
            # Reconstruct input path
            input_path = UPLOAD_DIR / f"{job_id}_{job['filename']}"
            
            # Construct command
            # We need to run this from the root of the repo so imports work
            cmd = [
                sys.executable,
                "-m",
                "render",
                "--replay",
                str(input_path.absolute())
            ]

            config = job['config']
            if config.get("anon"):
                cmd.append("--anon")
            if config.get("no_chat"):
                cmd.append("--no-chat")
            if config.get("no_logs"):
                cmd.append("--no-logs")
            if config.get("team_tracers"):
                cmd.append("--team-tracers")
            
            cmd.extend(["--fps", str(config.get("fps", 20))])
            cmd.extend(["--quality", str(config.get("quality", 7))])
            
            print(f"Starting job {job_id}: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(RENDERER_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Move output file to output dir
                # The renderer outputs .mp4 in the same dir as the replay
                original_output = input_path.with_suffix(".mp4")
                final_output = OUTPUT_DIR / f"{job_id}.mp4"
                
                if original_output.exists():
                    shutil.move(str(original_output), str(final_output))
                    
                    # Move JSON info file if it exists
                    original_json = input_path.with_suffix(".json")
                    # The renderer outputs {stem}-builds.json
                    original_json = input_path.parent / f"{input_path.stem}-builds.json"
                    final_json = OUTPUT_DIR / f"{job_id}.json"
                    
                    if original_json.exists():
                        shutil.move(str(original_json), str(final_json))
                        
                    database.update_job_status(job_id, JobStatus.COMPLETED, output_path=str(final_output))
                    
                    # Handle Discord Webhook
                    webhook_url = config.get("discord_webhook_url")
                    if webhook_url:
                        try:
                            async with httpx.AsyncClient() as client:
                                with open(final_output, "rb") as f:
                                    files = {"file": (final_output.name, f, "video/mp4")}
                                    webhook_response = await client.post(webhook_url, files=files)
                                    if webhook_response.status_code not in [200, 204]:
                                        print(f"Discord upload failed: {webhook_response.status_code} - {webhook_response.text}")
                        except Exception as e:
                            print(f"Discord upload error: {e}")

                else:
                    database.update_job_status(job_id, JobStatus.FAILED, message="Output file not found after rendering.")
                    print(f"Error: Output file not found: {original_output}")

            else:
                database.update_job_status(job_id, JobStatus.FAILED, message=f"Renderer failed with code {process.returncode}")
                print(f"Renderer failed: {stderr.decode()}")

        except Exception as e:
            database.update_job_status(job_id, JobStatus.FAILED, message=str(e))
            print(f"Job failed with exception: {e}")
        finally:
            queue.task_done()

async def get_session_id(response: Response, session_id: Optional[str] = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key="session_id", value=session_id, httponly=True)
    return session_id

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    max_workers = int(os.getenv("MAX_WORKERS", 1))
    print(f"Starting {max_workers} worker(s)")
    for _ in range(max_workers):
        asyncio.create_task(worker())
    yield

app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload", response_model=JobResponse)
async def upload_file(
    response: Response, 
    file: UploadFile = File(...), 
    session_id: str = Depends(get_session_id),
    anon: bool = Form(False),
    no_chat: bool = Form(False),
    no_logs: bool = Form(False),
    team_tracers: bool = Form(False),
    fps: int = Form(20),
    quality: int = Form(7),
    discord_webhook_url: Optional[str] = Form(None)
):
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    config = {
        "anon": anon,
        "no_chat": no_chat,
        "no_logs": no_logs,
        "team_tracers": team_tracers,
        "fps": fps,
        "quality": quality,
        "discord_webhook_url": discord_webhook_url
    }
    
    database.create_job(job_id, file.filename, session_id, config)
    
    await queue.put(job_id)
    
    return {
        "id": job_id,
        "filename": file.filename,
        "status": JobStatus.QUEUED,
        "message": "Queued for rendering"
    }

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(session_id: str = Depends(get_session_id)):
    user_jobs = database.get_jobs_by_session(session_id)
    return [
        {
            "id": job["id"],
            "filename": job["filename"],
            "status": job["status"],
            "message": job.get("message", "")
        }
        for job in user_jobs
    ]

@app.get("/api/stream/{job_id}")
async def stream_video(job_id: str, session_id: str = Depends(get_session_id)):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    output_path = Path(job.get("output_path")) if job.get("output_path") else None
    if not output_path or not output_path.exists():
         raise HTTPException(status_code=500, detail="Output file missing")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        content_disposition_type="inline"
    )

@app.get("/api/download/{job_id}")
async def download_video(job_id: str, session_id: str = Depends(get_session_id)):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    output_path = Path(job.get("output_path")) if job.get("output_path") else None
    if not output_path or not output_path.exists():
         raise HTTPException(status_code=500, detail="Output file missing")

    return FileResponse(
        path=output_path,
        filename=f"{Path(job['filename']).stem}.mp4",
        media_type="video/mp4"
    )

@app.get("/api/jobs/{job_id}/info")
async def get_job_info(job_id: str, session_id: str = Depends(get_session_id)):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    info_path = OUTPUT_DIR / f"{job_id}.json"
    if not info_path.exists():
         raise HTTPException(status_code=404, detail="Player info not found")

    return FileResponse(
        path=info_path,
        media_type="application/json"
    )

@app.get("/api/download-all")
async def download_all_videos(session_id: str = Depends(get_session_id)):
    jobs = database.get_jobs_by_session(session_id)
    completed_jobs = [
        job for job in jobs
        if job["status"] == JobStatus.COMPLETED
    ]
    
    if not completed_jobs:
        raise HTTPException(status_code=404, detail="No completed jobs found")
        
    # Create a zip file in memory
    import zipfile
    import io
    from datetime import datetime
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for job in completed_jobs:
            output_path = Path(job.get("output_path")) if job.get("output_path") else None
            if output_path and output_path.exists():
                zip_file.write(output_path, arcname=f"{Path(job['filename']).stem}.mp4")
    
    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"minimap_renders_{timestamp}.zip"
    
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
