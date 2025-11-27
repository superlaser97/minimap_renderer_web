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
    completed_at: Optional[str] = None

# Worker Queue
queue = asyncio.Queue()

def construct_discord_payload(json_path: Path) -> dict:
    import json
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            players = json.load(f)
            
        if not players:
            return {"content": "No player info available."}

        # Group by relation
        teams = {}
        for player in players:
            relation = player.get('relation', 2)
            if relation not in teams:
                teams[relation] = []
            teams[relation].append(player)
            
        # Identify "Player In Render"
        # The recording player typically has a relation that is not 0 (Ally) or 1 (Enemy).
        # It might be 2 (Neutral) or something else (e.g. -1, or a specific self-flag).
        # We'll assume anyone NOT 0 or 1 is the main player.
        main_players = []
        other_players = []
        
        for r, p_list in teams.items():
            # Convert relation to int just in case it's a string in JSON
            try:
                r_int = int(r)
            except:
                r_int = -999 # Treat unknown non-ints as potential main player?
                
            if r_int != 0 and r_int != 1:
                main_players.extend(p_list)
            else:
                other_players.extend(p_list)
        
        # Sort other players by name for consistency
        other_players.sort(key=lambda x: x.get('name', ''))

        embed = {
            "title": "Render Complete",
            "color": 0x57F287, # Discord Green
            "fields": []
        }

        # Field 1: Player In Render
        if main_players:
            # Assuming usually one, but handle multiple
            names = [f"{p.get('name', 'Unknown')} ({p.get('ship', 'Unknown Ship')})" for p in main_players]
            embed["fields"].append({
                "name": "Player In Render",
                "value": "\n".join(names),
                "inline": False
            })
        else:
             embed["fields"].append({
                "name": "Player In Render",
                "value": "Unknown",
                "inline": False
            })

        # Field 2: Other Players
        if other_players:
            # Just names, comma separated
            names = [p.get('name', 'Unknown') for p in other_players]
            # Discord field value limit is 1024 chars
            value = ", ".join(names)
            if len(value) > 1024:
                value = value[:1021] + "..."
            
            embed["fields"].append({
                "name": "Other Players",
                "value": value,
                "inline": False
            })

        return {"embeds": [embed]}

    except Exception as e:
        print(f"Error formatting Discord message: {e}")
        return {"content": "Error formatting player info."}

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
                            payload = {}
                            if final_json.exists():
                                payload = construct_discord_payload(final_json)

                            import json
                            async with httpx.AsyncClient() as client:
                                with open(final_output, "rb") as f:
                                    files = {"file": (final_output.name, f, "video/mp4")}
                                    # When sending files, JSON payload must be sent as 'payload_json' string
                                    data = {"payload_json": json.dumps(payload)}
                                    webhook_response = await client.post(webhook_url, data=data, files=files)
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

@app.get("/api/config/webhooks")
async def get_discord_webhooks():
    import json
    webhooks_env = os.getenv("DISCORD_WEBHOOKS", "[]")
    try:
        webhooks = json.loads(webhooks_env)
        return webhooks
    except json.JSONDecodeError:
        print("Error decoding DISCORD_WEBHOOKS environment variable")
        return []

@app.get("/api/jobs", response_model=List[JobResponse])
async def get_jobs(session_id: str = Depends(get_session_id)):
    user_jobs = database.get_jobs_by_session(session_id)
    return [
        {
            "id": job["id"],
            "filename": job["filename"],
            "status": job["status"],
            "message": job.get("message", ""),
            "completed_at": str(job["completed_at"]) if job.get("completed_at") else None
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

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str, session_id: str = Depends(get_session_id)):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("session_id") != session_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Delete files
    # 1. Upload file
    upload_path = UPLOAD_DIR / f"{job_id}_{job['filename']}"
    if upload_path.exists():
        try:
            os.remove(upload_path)
        except OSError as e:
            print(f"Error deleting upload file {upload_path}: {e}")

    # 2. Output file
    output_path = Path(job.get("output_path")) if job.get("output_path") else None
    if output_path and output_path.exists():
        try:
            os.remove(output_path)
        except OSError as e:
            print(f"Error deleting output file {output_path}: {e}")
            
    # 3. JSON info file
    json_path = OUTPUT_DIR / f"{job_id}.json"
    if json_path.exists():
        try:
            os.remove(json_path)
        except OSError as e:
            print(f"Error deleting json file {json_path}: {e}")

    # Delete from DB
    database.delete_job(job_id)
    
    return {"message": "Job deleted successfully"}

@app.get("/api/config/cleanup")
async def get_cleanup_config():
    cleanup_hours = int(os.getenv("CLEANUP_HOURS", 24))
    return {"hours": cleanup_hours}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
