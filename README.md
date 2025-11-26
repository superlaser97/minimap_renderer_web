# Web Wrapper for Minimap Renderer

![banner](image.png)

A web-based frontend for the Minimap Renderer, this allowing users to upload replays and download rendered videos in the browser. See the minimap renderer project here: https://github.com/WoWs-Builder-Team/minimap_renderer

## Table of Contents
- [Prerequisites](#prerequisites)
- [Running with npm](#running-with-npm)
- [Running with docker](#running-with-docker)
- [Usage](#usage)
- [Architecture](#architecture)
- [Roadmap](#roadmap)
- [Attribution](#attribution)

## Prerequisites
- Python 3.10+ (Python 3.14 is supported with the instructions below)
- Node.js and npm

## Running with npm
### 1. Set up a Python Virtual Environment

To avoid compatibility issues with system packages or other projects, it is **highly recommended** to use a virtual environment.

1.  Navigate to the project root:
    ```bash
    cd c:/Users/USER/Desktop/minimap_renderer-master
    ```

2.  Create a virtual environment (named `venv`):
    ```bash
    python -m venv venv
    ```

3.  Activate the virtual environment:
    *   **Windows**:
        ```cmd
        .\venv\Scripts\activate.bat
        ```
    *   **Linux/Mac**:
        ```bash
        source venv/bin/activate
        ```

### 2. Install Backend Dependencies

The original `requirements.txt` may fail on newer Python versions due to strict version pinning. We have provided `requirements_modern.txt` with relaxed constraints for compatibility.

1.  Install the dependencies:
    ```bash
    pip install -r requirements_modern.txt
    ```

### 3. Install Frontend Dependencies

1.  Navigate to the frontend directory:
    ```bash
    cd web_wrapper/frontend
    ```

2.  Install Node modules:
    ```bash
    npm install
    ```

### 4. Run the Application

A helper script `run.py` is provided in the `web_wrapper` directory to start both the backend and frontend servers simultaneously.

1.  Navigate to the `web_wrapper` directory:
    ```bash
    cd ../
    ```

2.  Run the script (ensure your virtual environment is activated):
    ```bash
    python run.py
    ```

You should see output indicating that both services have started:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173

## Running with docker

You can also run the entire application using Docker Compose.

1.  Ensure you have Docker and Docker Compose installed.
2.  Run the following command in the project root:
    ```bash
    docker-compose up --build
    ```
3.  Access the application at `http://localhost:5173`.

## Usage

1.  Open your browser to `http://localhost:5173`.
2.  **Upload**: Drag and drop your `.wowsreplay` files into the upload zone.
3.  **Queue**: Watch the status of your jobs in the list below.
4.  **Download**: Once a job is `completed`, click the "Download" button to get your MP4 video.

## Architecture

- **Backend**: FastAPI app (`backend/main.py`) that manages a job queue and executes the original `render` module via subprocess.
- **Frontend**: React/Vite app (`frontend/`) with TailwindCSS for styling.
- **Storage**:
    - Uploads are stored in `web_wrapper/backend/uploads`.
    - Generated videos are moved to `web_wrapper/backend/outputs`.

# Roadmap

- [ ] Delete rendered videos after download or after a certain amount of time
- [ ] Uploading directly to discord
- [ ] Add support to customize the output video

## Attribution

This project uses the [Minimap Renderer](https://github.com/WoWs-Builder-Team/minimap_renderer) by the WoWs-Builder-Team.

