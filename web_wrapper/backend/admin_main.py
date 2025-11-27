import os
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
import database
from datetime import datetime, timedelta

# Configuration
CLEANUP_HOURS = int(os.getenv("CLEANUP_HOURS", 24))
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")

# Ensure directories exist (though main app should have created them)
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def cleanup_task():
    while True:
        try:
            logger.info(f"Running cleanup task. Deleting jobs older than {CLEANUP_HOURS} hours.")
            
            # Get jobs to clean up
            old_jobs = database.get_old_completed_jobs(CLEANUP_HOURS)
            
            for job in old_jobs:
                job_id = job['id']
                logger.info(f"Cleaning up job {job_id}")
                
                # Delete files
                input_path = UPLOAD_DIR / f"{job_id}_{job['filename']}"
                if input_path.exists():
                    input_path.unlink()
                
                if job['output_path']:
                    output_path = Path(job['output_path'])
                    if output_path.exists():
                        output_path.unlink()
                        
                info_path = OUTPUT_DIR / f"{job_id}.json"
                if info_path.exists():
                    info_path.unlink()
                    
                database.delete_job(job_id)
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_task())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

class JobModel(BaseModel):
    id: str
    filename: str
    status: str
    message: Optional[str]
    created_at: str
    completed_at: Optional[str]

@app.get("/admin/jobs", response_model=List[JobModel])
async def get_all_jobs():
    jobs = database.get_all_jobs()
    return jobs

@app.delete("/admin/jobs/{job_id}")
async def delete_job(job_id: str):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # Delete files
    input_path = UPLOAD_DIR / f"{job_id}_{job['filename']}"
    if input_path.exists():
        input_path.unlink()
    
    if job['output_path']:
        output_path = Path(job['output_path'])
        if output_path.exists():
            output_path.unlink()
            
    info_path = OUTPUT_DIR / f"{job_id}.json"
    if info_path.exists():
        info_path.unlink()
        
    database.delete_job(job_id)
    return {"message": "Job deleted"}

@app.delete("/admin/jobs")
async def delete_all_jobs():
    # Delete all files
    for file in UPLOAD_DIR.glob("*"):
        if file.is_file():
            file.unlink()
            
    for file in OUTPUT_DIR.glob("*"):
        if file.is_file():
            file.unlink()
            
    database.delete_all_jobs()
    return {"message": "All jobs deleted"}

@app.get("/admin/jobs/{job_id}/video")
async def get_admin_video(job_id: str):
    job = database.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['output_path']:
        output_path = Path(job['output_path'])
        if output_path.exists():
            return FileResponse(path=output_path, media_type="video/mp4")
    
    raise HTTPException(status_code=404, detail="Video file not found")

@app.get("/admin/jobs/{job_id}/info")
async def get_admin_info(job_id: str):
    info_path = OUTPUT_DIR / f"{job_id}.json"
    if info_path.exists():
        return FileResponse(path=info_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="Player info not found")

@app.get("/", response_class=HTMLResponse)
async def admin_ui():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Minimap Renderer Admin</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest"></script>
    </head>
    <body class="bg-slate-900 text-slate-200 p-8">
        <div class="max-w-7xl mx-auto">
            <div class="flex justify-between items-center mb-8">
                <h1 class="text-3xl font-bold text-white">Minimap Renderer Admin</h1>
                <div class="flex items-center gap-4">
                    <div class="text-sm text-slate-400">
                        Cleanup Period: <span class="font-mono text-white bg-slate-800 px-2 py-1 rounded">""" + str(CLEANUP_HOURS) + """ hours</span>
                    </div>
                    <button onclick="confirmDeleteAll()" class="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                        Delete All
                    </button>
                </div>
            </div>
            
            <div class="bg-slate-800 rounded-xl overflow-hidden border border-slate-700 shadow-xl">
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-900/50 text-slate-400 uppercase text-xs font-medium">
                        <tr>
                            <th class="px-6 py-4">Status</th>
                            <th class="px-6 py-4">ID</th>
                            <th class="px-6 py-4">Filename</th>
                            <th class="px-6 py-4">Created At</th>
                            <th class="px-6 py-4">Completed At</th>
                            <th class="px-6 py-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="jobs-table" class="divide-y divide-slate-700">
                        <!-- Jobs will be populated here -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Video Modal -->
        <div id="video-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm hidden">
            <div class="relative w-full max-w-5xl bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10">
                <div class="flex items-center justify-between p-4 border-b border-white/5 bg-white/5">
                    <h3 class="text-lg font-medium text-white">Video Preview</h3>
                    <button onclick="closeVideoModal()" class="p-2 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors">
                        <i data-lucide="x" class="w-5 h-5"></i>
                    </button>
                </div>
                <div class="aspect-video bg-black">
                    <video id="modal-video" controls class="w-full h-full"></video>
                </div>
            </div>
        </div>

        <!-- Info Modal -->
        <div id="info-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm hidden">
            <div class="relative w-full max-w-4xl bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10 max-h-[90vh] flex flex-col">
                <div class="flex items-center justify-between p-6 border-b border-white/10 bg-slate-900/50 backdrop-blur-md sticky top-0 z-10">
                    <h3 class="text-xl font-semibold text-white flex items-center gap-2">
                        <i data-lucide="users" class="w-5 h-5 text-blue-400"></i>
                        Player Information
                    </h3>
                    <button onclick="closeInfoModal()" class="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-full transition-colors">
                        <i data-lucide="x" class="w-5 h-5"></i>
                    </button>
                </div>
                <div id="info-content" class="overflow-y-auto p-6 space-y-8">
                    <!-- Player info will be populated here -->
                </div>
            </div>
        </div>

        <!-- Confirmation Modal -->
        <div id="confirm-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm hidden animate-in fade-in duration-200">
            <div class="relative w-full max-w-md bg-slate-900 rounded-2xl overflow-hidden shadow-2xl border border-white/10 p-6 animate-in zoom-in-95 duration-200">
                <div class="flex flex-col items-center text-center">
                    <div class="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
                        <i data-lucide="alert-triangle" class="w-6 h-6 text-red-400"></i>
                    </div>
                    <h3 class="text-xl font-semibold text-white mb-2">Are you sure?</h3>
                    <p id="confirm-message" class="text-slate-400 mb-6">This action cannot be undone.</p>
                    <div class="flex gap-3 w-full">
                        <button onclick="closeConfirmModal()" class="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-medium transition-colors">
                            Cancel
                        </button>
                        <button id="confirm-btn" class="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium transition-colors shadow-lg shadow-red-500/20">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <script>
            lucide.createIcons();
            let pendingDeleteId = null;
            let isDeleteAll = false;

            async function fetchJobs() {
                const response = await fetch('/admin/jobs');
                const jobs = await response.json();
                const tbody = document.getElementById('jobs-table');
                tbody.innerHTML = '';

                jobs.forEach(job => {
                    const tr = document.createElement('tr');
                    tr.className = 'hover:bg-slate-700/50 transition-colors';
                    
                    let statusColor = 'text-slate-400';
                    if (job.status === 'completed') statusColor = 'text-emerald-400';
                    if (job.status === 'failed') statusColor = 'text-red-400';
                    if (job.status === 'processing') statusColor = 'text-blue-400';

                    let actions = '';
                    if (job.status === 'completed') {
                        actions += `
                            <button onclick="openVideo('${job.id}')" class="text-blue-400 hover:text-blue-300 hover:bg-blue-400/10 px-3 py-1.5 rounded-lg transition-colors text-xs font-medium border border-blue-400/20 mr-2">
                                Watch
                            </button>
                            <button onclick="openInfo('${job.id}')" class="text-indigo-400 hover:text-indigo-300 hover:bg-indigo-400/10 px-3 py-1.5 rounded-lg transition-colors text-xs font-medium border border-indigo-400/20 mr-2">
                                Info
                            </button>
                        `;
                    }
                    actions += `
                        <button onclick="confirmDeleteJob('${job.id}')" class="text-red-400 hover:text-red-300 hover:bg-red-400/10 px-3 py-1.5 rounded-lg transition-colors text-xs font-medium border border-red-400/20">
                            Delete
                        </button>
                    `;

                    tr.innerHTML = `
                        <td class="px-6 py-4 font-medium ${statusColor} capitalize">${job.status}</td>
                        <td class="px-6 py-4 font-mono text-xs text-slate-500">${job.id.substring(0, 8)}...</td>
                        <td class="px-6 py-4 text-white">${job.filename}</td>
                        <td class="px-6 py-4 text-slate-400">${new Date(job.created_at).toLocaleString()}</td>
                        <td class="px-6 py-4 text-slate-400">${job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}</td>
                        <td class="px-6 py-4 text-right">
                            ${actions}
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                lucide.createIcons();
            }

            function confirmDeleteJob(id) {
                pendingDeleteId = id;
                isDeleteAll = false;
                document.getElementById('confirm-message').textContent = 'This will permanently delete this job and its files.';
                document.getElementById('confirm-modal').classList.remove('hidden');
            }

            function confirmDeleteAll() {
                isDeleteAll = true;
                document.getElementById('confirm-message').textContent = 'This will permanently delete ALL jobs and files. This cannot be undone.';
                document.getElementById('confirm-modal').classList.remove('hidden');
            }

            function closeConfirmModal() {
                document.getElementById('confirm-modal').classList.add('hidden');
                pendingDeleteId = null;
                isDeleteAll = false;
            }

            document.getElementById('confirm-btn').onclick = async () => {
                try {
                    if (isDeleteAll) {
                        await fetch('/admin/jobs', { method: 'DELETE' });
                    } else if (pendingDeleteId) {
                        await fetch(`/admin/jobs/${pendingDeleteId}`, { method: 'DELETE' });
                    }
                    fetchJobs();
                    closeConfirmModal();
                } catch (error) {
                    alert('Failed to delete');
                    console.error(error);
                }
            };

            function openVideo(id) {
                const modal = document.getElementById('video-modal');
                const video = document.getElementById('modal-video');
                video.src = `/admin/jobs/${id}/video`;
                modal.classList.remove('hidden');
                video.play();
            }

            function closeVideoModal() {
                const modal = document.getElementById('video-modal');
                const video = document.getElementById('modal-video');
                video.pause();
                video.src = '';
                modal.classList.add('hidden');
            }

            async function openInfo(id) {
                try {
                    const response = await fetch(`/admin/jobs/${id}/info`);
                    if (!response.ok) throw new Error('Info not found');
                    const players = await response.json();
                    
                    const modal = document.getElementById('info-modal');
                    const content = document.getElementById('info-content');
                    
                    // Group players
                    const teams = { 0: [], 1: [], 2: [] };
                    players.forEach(p => {
                        if (teams[p.relation] !== undefined) teams[p.relation].push(p);
                    });

                    let html = '';
                    const relations = [0, 1, 2]; // Ally, Enemy, Neutral
                    const labels = { 0: 'Ally', 1: 'Enemy', 2: 'Neutral' };
                    const colors = { 0: 'text-green-400 border-green-400/20 bg-green-400/10', 1: 'text-red-400 border-red-400/20 bg-red-400/10', 2: 'text-yellow-400 border-yellow-400/20 bg-yellow-400/10' };

                    relations.forEach(relation => {
                        if (teams[relation].length > 0) {
                            html += `
                                <div class="space-y-4">
                                    <h4 class="text-sm font-bold uppercase tracking-wider px-3 py-1 rounded-full w-fit border ${colors[relation]}">
                                        ${labels[relation]}
                                    </h4>
                                    <div class="overflow-x-auto rounded-xl border border-white/5 bg-white/5">
                                        <table class="w-full text-left text-sm">
                                            <thead class="bg-white/5 text-slate-400">
                                                <tr>
                                                    <th class="px-6 py-3 font-medium">Player</th>
                                                    <th class="px-6 py-3 font-medium">Clan</th>
                                                    <th class="px-6 py-3 font-medium">Ship</th>
                                                    <th class="px-6 py-3 font-medium text-right">Build</th>
                                                </tr>
                                            </thead>
                                            <tbody class="divide-y divide-white/5">
                                                ${teams[relation].map(player => `
                                                    <tr class="hover:bg-white/5 transition-colors">
                                                        <td class="px-6 py-4 font-medium text-white">${player.name}</td>
                                                        <td class="px-6 py-4 text-slate-300">${player.clan ? `[${player.clan}]` : '-'}</td>
                                                        <td class="px-6 py-4 text-slate-300">${player.ship}</td>
                                                        <td class="px-6 py-4 text-right">
                                                            ${player.build_url ? `<a href="${player.build_url}" target="_blank" class="text-blue-400 hover:text-blue-300 hover:underline">View Build</a>` : '<span class="text-slate-600">No Build</span>'}
                                                        </td>
                                                    </tr>
                                                `).join('')}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            `;
                        }
                    });

                    content.innerHTML = html;
                    modal.classList.remove('hidden');
                } catch (error) {
                    alert('Failed to load player info');
                    console.error(error);
                }
            }

            function closeInfoModal() {
                document.getElementById('info-modal').classList.add('hidden');
            }

            // Initial fetch and poll every 5 seconds
            fetchJobs();
            setInterval(fetchJobs, 5000);
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
