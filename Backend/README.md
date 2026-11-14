# Moonscape Backend Application

FastAPI service for lunar landing site exploration and topographic analysis.

## Running Tests
From this directory:
```powershell
..\.venv\Scripts\pytest -v
```

## Running the Server
From this directory:
```powershell
..\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Or from the project root (`D:\MoonScape`):
```powershell
uvicorn Backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
