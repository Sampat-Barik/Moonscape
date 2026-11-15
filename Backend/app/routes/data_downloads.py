"""API endpoints for controlling and tracking NASA dataset downloads."""

from typing import List
from fastapi import APIRouter, HTTPException, Path as FPath

from app.config.dataset_settings import dataset_settings
from app.schemas.dataset_schemas import DownloadTaskResponse
from app.services.data_management.download_manager import download_manager

router = APIRouter(prefix="/data", tags=["NASA Data Downloads"])


@router.post(
    "/download/{dataset_id}",
    response_model=DownloadTaskResponse,
    summary="Trigger controlled background streaming download of a NASA dataset",
)
def trigger_dataset_download(
    dataset_id: str = FPath(..., description="Unique dataset ID from catalog"),
) -> DownloadTaskResponse:
    """Initiates an asynchronous resume-capable streaming download for the specified dataset."""
    dataset = dataset_settings.datasets.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found in manifest catalog.")

    task = download_manager.start_download(dataset)
    return DownloadTaskResponse(**task.to_dict())


@router.post(
    "/download/profile/{profile_name}",
    response_model=List[DownloadTaskResponse],
    summary="Enqueue all datasets for a predefined profile (e.g. profile_a, profile_b, profile_c)",
)
def trigger_profile_download(
    profile_name: str = FPath(..., description="Profile identifier: 'profile_a', 'profile_b', or 'profile_c'"),
) -> List[DownloadTaskResponse]:
    """Enqueues streaming downloads for all datasets defined within the profile."""
    profiles = dataset_settings.get_profiles()
    if profile_name not in profiles:
        raise HTTPException(
            status_code=404,
            detail=f"Profile '{profile_name}' not found. Available: {list(profiles.keys())}",
        )

    dataset_ids = profiles[profile_name].get("datasets", [])
    tasks = []
    for d_id in dataset_ids:
        dataset = dataset_settings.datasets.get(d_id)
        if dataset:
            task = download_manager.start_download(dataset)
            tasks.append(DownloadTaskResponse(**task.to_dict()))

    return tasks


@router.get(
    "/downloads",
    response_model=List[DownloadTaskResponse],
    summary="List all active and recent dataset download tasks",
)
def list_download_tasks() -> List[DownloadTaskResponse]:
    """Returns a list of all current background download tasks and their progress."""
    return [DownloadTaskResponse(**t.to_dict()) for t in download_manager.get_all_tasks()]


@router.get(
    "/downloads/{task_id}",
    response_model=DownloadTaskResponse,
    summary="Get status, streaming speed, and progress of a download task",
)
def get_download_task_status(
    task_id: str = FPath(..., description="Download Task ID (e.g. DL-XXXXXXXX)"),
) -> DownloadTaskResponse:
    """Returns real-time progress percentage, transfer speed in MB/s, and completion state."""
    task = download_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Download task '{task_id}' not found.")
    return DownloadTaskResponse(**task.to_dict())


@router.post(
    "/downloads/{task_id}/cancel",
    summary="Cancel an active or queued download task",
)
def cancel_download_task(
    task_id: str = FPath(..., description="Download Task ID to cancel"),
) -> dict:
    """Stops the streaming thread and marks the task as cancelled."""
    success = download_manager.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Task '{task_id}' could not be cancelled (either not found or already completed/failed).",
        )
    return {"task_id": task_id, "status": "cancelled", "message": "Download task successfully cancelled."}
