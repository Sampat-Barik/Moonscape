"""Background streaming download manager with byte-range resume, disk checks, and progress tracking."""

import ssl
import threading
import time
import urllib.request
import uuid
from typing import Dict, Optional
import certifi

from Backend.app.config.dataset_settings import DatasetDefinition, DatasetStatus
from Backend.app.config.resource_settings import resource_settings
from Backend.app.core.logging import logger
from Backend.app.services.data_management.dataset_registry import dataset_registry
from Backend.app.services.data_management.local_storage import local_storage

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MoonscapeNASAClient/2.0"


class DownloadTask:
    """Tracks state and progress of an active or completed download."""

    def __init__(self, task_id: str, dataset: DatasetDefinition):
        self.task_id = task_id
        self.dataset = dataset
        self.status: str = "queued"
        self.bytes_downloaded: int = 0
        self.total_bytes: int = dataset.size_bytes
        self.progress_pct: float = 0.0
        self.speed_mbps: float = 0.0
        self.error_message: Optional[str] = None
        self.start_time: float = time.time()
        self.cancelled: bool = False

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "dataset_id": self.dataset.id,
            "filename": self.dataset.filename,
            "status": self.status,
            "bytes_downloaded": self.bytes_downloaded,
            "total_bytes": self.total_bytes,
            "progress_pct": round(self.progress_pct, 1),
            "speed_mbps": round(self.speed_mbps, 2),
            "error_message": self.error_message,
        }


class DownloadManager:
    """Coordinates controlled NASA data acquisition with hardware guards."""

    def __init__(self):
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(resource_settings.MAX_CONCURRENT_LARGE_DOWNLOADS)
        self._tasks: Dict[str, DownloadTask] = {}

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list:
        return list(self._tasks.values())

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in ["queued", "downloading"]:
            task.cancelled = True
            task.status = "cancelled"
            logger.info("Download task %s cancelled by user request.", task_id)
            return True
        return False

    def start_download(self, dataset: DatasetDefinition) -> DownloadTask:
        """Enqueues and starts a background streaming download task."""
        task_id = f"DL-{uuid.uuid4().hex[:8].upper()}"
        task = DownloadTask(task_id, dataset)
        self._tasks[task_id] = task

        thread = threading.Thread(target=self._download_worker, args=(task,), daemon=True)
        thread.start()
        return task

    def _download_worker(self, task: DownloadTask) -> None:
        """Worker thread executing the resume-capable streaming download."""
        dataset = task.dataset
        dest_path = dataset.absolute_local_path
        part_path = local_storage.get_temp_part_path(dataset.filename)

        # 1. Check disk space headroom
        free_gb = resource_settings.get_available_disk_space_gb(dest_path)
        required_gb = dataset.size_mb / 1024.0
        if free_gb - required_gb < resource_settings.MINIMUM_FREE_SSD_HEADROOM_GB:
            task.status = "failed"
            task.error_message = (
                f"Insufficient SSD storage on target drive. "
                f"Available: {free_gb:.2f} GB, Required: {required_gb:.2f} GB, "
                f"Minimum safety headroom: {resource_settings.MINIMUM_FREE_SSD_HEADROOM_GB} GB."
            )
            dataset_registry.set_status(dataset.id, DatasetStatus.FAILED, task.error_message)
            logger.error("Download blocked: %s", task.error_message)
            return

        with self._semaphore:
            if task.cancelled:
                return

            task.status = "downloading"
            dataset_registry.set_status(dataset.id, DatasetStatus.DOWNLOADING)

            # Determine existing bytes for HTTP Range resume
            existing_bytes = part_path.stat().st_size if part_path.exists() else 0
            task.bytes_downloaded = existing_bytes

            headers = {"User-Agent": USER_AGENT}
            if existing_bytes > 0:
                headers["Range"] = f"bytes={existing_bytes}-"
                logger.info("Resuming %s from byte %d", dataset.filename, existing_bytes)

            req = urllib.request.Request(dataset.url, headers=headers)
            try:
                with urllib.request.urlopen(req, context=SSL_CTX, timeout=resource_settings.DOWNLOAD_TIMEOUT_SECONDS) as resp:
                    # Check status code (200 = full file, 206 = partial content)
                    is_resume = (resp.status == 206)
                    write_mode = "ab" if is_resume and existing_bytes > 0 else "wb"
                    if not is_resume and existing_bytes > 0:
                        existing_bytes = 0
                        task.bytes_downloaded = 0

                    content_len_hdr = resp.headers.get("Content-Length")
                    if content_len_hdr:
                        server_remaining = int(content_len_hdr)
                        task.total_bytes = existing_bytes + server_remaining
                    else:
                        task.total_bytes = dataset.size_bytes

                    chunk_size = resource_settings.DOWNLOAD_CHUNK_SIZE_BYTES
                    last_time = time.time()
                    bytes_since_last = 0

                    with open(part_path, write_mode) as f:
                        while True:
                            if task.cancelled:
                                logger.info("Task %s cancelled during stream.", task.task_id)
                                return

                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break

                            f.write(chunk)
                            task.bytes_downloaded += len(chunk)
                            bytes_since_last += len(chunk)

                            now = time.time()
                            elapsed = now - last_time
                            if elapsed >= 0.5:
                                task.speed_mbps = (bytes_since_last / (1024 * 1024)) / elapsed
                                task.progress_pct = min(100.0, (task.bytes_downloaded / max(1, task.total_bytes)) * 100.0)
                                last_time = now
                                bytes_since_last = 0

                # Download finished, now validate
                task.status = "validating"
                dataset_registry.set_status(dataset.id, DatasetStatus.VALIDATING)
                task.progress_pct = 100.0

                is_valid, reason = local_storage.validate_geotiff(part_path)
                if not is_valid:
                    task.status = "failed"
                    task.error_message = f"Downloaded GeoTIFF failed validation: {reason}"
                    dataset_registry.set_status(dataset.id, DatasetStatus.INVALID, reason)
                    return

                # Atomic rename
                success = local_storage.finalize_atomic_download(part_path, dest_path)
                if success:
                    task.status = "completed"
                    dataset_registry.set_status(dataset.id, DatasetStatus.AVAILABLE, "Validated authentic NASA GeoTIFF.")
                    logger.info("Successfully acquired NASA dataset: %s", dataset.id)
                else:
                    task.status = "failed"
                    task.error_message = "Failed to atomically move validated file to permanent storage."
                    dataset_registry.set_status(dataset.id, DatasetStatus.FAILED, task.error_message)

            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)
                dataset_registry.set_status(dataset.id, DatasetStatus.FAILED, str(e))
                logger.error("Error downloading %s: %s", dataset.filename, str(e))


download_manager = DownloadManager()
