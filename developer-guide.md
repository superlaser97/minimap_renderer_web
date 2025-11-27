# Developer Guide

This guide provides technical details for developers working on the Minimap Renderer Web Wrapper.

## Project Structure

```
minimap_renderer_web/
├── minimap_renderer/       # The core renderer submodule (git submodule)
├── web_wrapper/
│   ├── backend/            # FastAPI backend
│   │   ├── main.py         # Main application entry point
│   │   ├── admin_main.py   # Admin application entry point
│   │   ├── database.py     # Database interaction layer
│   │   ├── run.py          # Helper script to run both servers
│   │   ├── uploads/        # Temporary storage for uploaded replays
│   │   └── outputs/        # Storage for rendered videos and JSON info
│   └── frontend/           # React frontend
│       ├── src/            # Source code
│       └── public/         # Static assets
├── docker-compose.yml      # Docker orchestration
└── README.md               # General project documentation
```

## Backend Development

The backend is built with **FastAPI** and uses **SQLite** for data persistence.

### Setup

1.  Create and activate a virtual environment.
2.  Install dependencies: `pip install -r requirements_modern.txt`.

### Key Files

-   **`main.py`**: Handles public API endpoints (`/upload`, `/jobs/{id}`, `/download/{id}`). It manages the job queue and spawns worker tasks.
-   **`admin_main.py`**: Handles admin API endpoints (`/admin/jobs`, `/admin/jobs/{id}/video`). It runs on a separate port (8001) and provides the Admin UI.
-   **`database.py`**: Contains all database logic. It uses a context manager for connections to ensure they are closed properly.

### API Endpoints

**Main App (Port 8000)**
-   `POST /upload`: Upload a `.wowsreplay` file.
-   `GET /jobs/{job_id}`: Get job status.
-   `GET /download/{job_id}`: Download the rendered video.
-   `GET /stream/{job_id}`: Stream the rendered video.

**Admin App (Port 8001)**
-   `GET /`: Serves the Admin UI HTML.
-   `GET /admin/jobs`: List all jobs.
-   `DELETE /admin/jobs/{job_id}`: Delete a specific job and its files.
-   `DELETE /admin/jobs`: Delete ALL jobs and files.
-   `GET /admin/jobs/{job_id}/video`: Serve video for admin preview.
-   `GET /admin/jobs/{job_id}/info`: Serve player info JSON.

## Frontend Development

The frontend is a **React** application built with **Vite** and styled with **TailwindCSS**.

### Setup

1.  Navigate to `web_wrapper/frontend`.
2.  Install dependencies: `npm install`.
3.  Run development server: `npm run dev`.

### Key Components

-   **Upload Area**: Handles file drag-and-drop and upload progress.
-   **Job List**: Polls the backend for job status and updates the UI.
-   **Video Player**: HTML5 video player for previewing results.

## Database Schema

The application uses a single table `jobs` in SQLite.

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    status TEXT NOT NULL,       -- 'processing', 'completed', 'failed'
    message TEXT,               -- Error message or status details
    session_id TEXT,            -- For grouping user uploads (optional)
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    config TEXT,                -- JSON string of render configuration
    output_path TEXT            -- Path to the generated video file
)
```

## Docker

The project uses a multi-container setup defined in `docker-compose.yml`.

-   **backend**: Runs `main.py` on port 8000.
-   **admin**: Runs `admin_main.py` on port 8001.
-   **frontend**: Serves the built React app via Nginx (or Vite in dev) on port 5173.

### Environment Variables

-   `MAX_WORKERS`: Controls the number of parallel rendering tasks in the backend.
-   `CLEANUP_HOURS`: Controls the age of jobs to be auto-deleted by the admin service.
-   `DB_PATH`: Location of the SQLite database.

## Testing & Verification

Refer to `walkthrough.md` for manual verification steps.
