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

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
RENDERER_ROOT = Path("../../minimap_renderer/src").resolve() # Pointing to the src directory where render.py lives

# Ensure directories exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Job Store (In-memory for simplicity)
jobs: Dict[str, Dict] = {}

class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str = ""

# Worker Queue
queue = asyncio.Queue()

async def worker():
    while True:
        job_id = await queue.get()
        job = jobs[job_id]
        
        try:
            jobs[job_id]["status"] = JobStatus.PROCESSING
            input_path = job["input_path"]
            
            # Construct command
            # We need to run this from the root of the repo so imports work
            cmd = [
                sys.executable,
                "-m",
                "render",
                "--replay",
                str(input_path.absolute())
            ]

            if job.get("anon"):
                cmd.append("--anon")
            if job.get("no_chat"):
                cmd.append("--no-chat")
            if job.get("no_logs"):
                cmd.append("--no-logs")
            if job.get("team_tracers"):
                cmd.append("--team-tracers")
            
            cmd.extend(["--fps", str(job.get("fps", 20))])
            cmd.extend(["--quality", str(job.get("quality", 7))])
            
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
                    jobs[job_id]["status"] = JobStatus.COMPLETED
                    jobs[job_id]["output_path"] = final_output
                else:
                    jobs[job_id]["status"] = JobStatus.FAILED
                    jobs[job_id]["message"] = "Output file not found after rendering."
                    print(f"Error: Output file not found: {original_output}")

            else:
                jobs[job_id]["status"] = JobStatus.FAILED
                jobs[job_id]["message"] = f"Renderer failed with code {process.returncode}"
                print(f"Renderer failed: {stderr.decode()}")

        except Exception as e:
            jobs[job_id]["status"] = JobStatus.FAILED
            jobs[job_id]["message"] = str(e)
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
    quality: int = Form(7)
):
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    
    jobs[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "status": JobStatus.QUEUED,
        "input_path": file_path,
        "input_path": file_path,
        "message": "",
        "session_id": session_id,
        "anon": anon,
        "no_chat": no_chat,
        "no_logs": no_logs,
        "team_tracers": team_tracers,
        "fps": fps,
        "quality": quality
    }
    
    await queue.put(job_id)
    
    return {
        "id": job_id,
        "filename": file.filename,
        "status": JobStatus.QUEUED,
        "message": "Queued for rendering"
    }

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(session_id: str = Depends(get_session_id)):
    user_jobs = [job for job in jobs.values() if job.get("session_id") == session_id]
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
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    output_path = job.get("output_path")
    if not output_path or not output_path.exists():
         raise HTTPException(status_code=500, detail="Output file missing")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        content_disposition_type="inline"
    )

@app.get("/api/download/{job_id}")
async def download_video(job_id: str, session_id: str = Depends(get_session_id)):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")

    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    output_path = job.get("output_path")
    if not output_path or not output_path.exists():
         raise HTTPException(status_code=500, detail="Output file missing")

    return FileResponse(
        path=output_path,
        filename=f"{Path(job['filename']).stem}.mp4",
        media_type="video/mp4"
    )

@app.get("/api/download-all")
async def download_all_videos(session_id: str = Depends(get_session_id)):
    completed_jobs = [
        job for job in jobs.values() 
        if job["status"] == JobStatus.COMPLETED and job.get("session_id") == session_id
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
            output_path = job.get("output_path")
            if output_path and output_path.exists():
                zip_file.write(output_path, arcname=f"{Path(job['filename']).stem}.mp4")
    
    zip_buffer.seek(0)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"minimap_renders_{timestamp}.zip"
    
    # We need to return a streaming response for in-memory files or save to disk first
    # For simplicity/robustness with FastAPI's FileResponse, let's save to a temp file or just stream bytes
    # StreamingResponse is better for in-memory
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
