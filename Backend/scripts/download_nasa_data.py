"""NASA Lunar Data Downloader CLI for Moonscape.

Acquires official USGS / NASA GSFC LOLA South Pole terrain products with HTTP Range resume,
free SSD headroom validation, and Rasterio integrity verification.
"""

import argparse
import sys
import time
from pathlib import Path

# Add project roots
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.dataset_settings import dataset_settings
from app.config.resource_settings import resource_settings
from app.services.data_management.dataset_registry import dataset_registry
from app.services.data_management.download_manager import download_manager
from app.services.data_management.local_storage import local_storage


def download_datasets(dataset_ids: list[str]) -> bool:
    print("=" * 70)
    print("MOONSCAPE NASA LUNAR DATA ACQUISITION")
    print(f"Hardware Profile: Ryzen 9 8940HX | 16 GB RAM | RTX 5070")
    print("=" * 70)

    # 1. Check disk space
    free_gb = resource_settings.get_available_disk_space_gb()
    print(f"Target Drive Free Storage: {free_gb:.2f} GB")
    if free_gb < resource_settings.MINIMUM_FREE_SSD_HEADROOM_GB:
        print(f"ERROR: Free SSD space ({free_gb:.2f} GB) is below safety limit ({resource_settings.MINIMUM_FREE_SSD_HEADROOM_GB} GB).")
        return False

    total_requested_mb = sum(
        dataset_settings.datasets[d_id].size_mb
        for d_id in dataset_ids
        if d_id in dataset_settings.datasets
    )
    print(f"Total Datasets to Acquire: {len(dataset_ids)} ({total_requested_mb:.1f} MB / {total_requested_mb/1024:.2f} GB)")
    print("-" * 70)

    all_success = True
    for idx, d_id in enumerate(dataset_ids, 1):
        defn = dataset_settings.datasets.get(d_id)
        if not defn:
            print(f"[{idx}/{len(dataset_ids)}] Skipping unknown dataset ID: {d_id}")
            continue

        dest_path = defn.absolute_local_path
        if dest_path.exists():
            is_valid, reason = local_storage.validate_geotiff(dest_path)
            if is_valid:
                print(f"[{idx}/{len(dataset_ids)}] {defn.filename} already present and verified ({defn.size_mb:.1f} MB). Skipping.")
                continue

        print(f"[{idx}/{len(dataset_ids)}] Downloading {defn.name} ({defn.size_mb:.1f} MB)...")
        print(f"  URL: {defn.url}")
        print(f"  Destination: {dest_path}")

        task = download_manager.start_download(defn)

        # Monitor progress
        last_pct = -1.0
        while task.status in ["queued", "downloading", "validating"]:
            pct = task.progress_pct
            if int(pct) != int(last_pct):
                mb_done = task.bytes_downloaded / (1024 * 1024)
                mb_total = task.total_bytes / (1024 * 1024)
                print(f"  Progress: {pct:.1f}% ({mb_done:.1f}/{mb_total:.1f} MB) @ {task.speed_mbps:.2f} MB/s", end="\r", flush=True)
                last_pct = pct
            time.sleep(0.5)

        print()  # newline
        if task.status == "completed":
            print(f"  [OK] Successfully downloaded and verified: {defn.filename}")
        else:
            print(f"  [FAILED] Download failed: {task.error_message}")
            all_success = False

        print("-" * 70)

    # Final summary
    dataset_registry.refresh_all_statuses()
    installed = dataset_registry.get_installed_datasets()
    print("\nFINAL INSTALLATION STATUS:")
    print(f"Verified Datasets on Local Disk: {len(installed)} / {len(dataset_settings.datasets)}")
    for d in installed:
        print(f"  - {d.name} ({d.size_mb:.1f} MB) -> {d.absolute_local_path.name}")

    return all_success


def main():
    parser = argparse.ArgumentParser(description="Download official NASA lunar terrain datasets for Moonscape.")
    parser.add_argument(
        "--profile",
        choices=["profile_a", "profile_b", "profile_c"],
        default="profile_b",
        help="Preset download profile: profile_a (min ~521MB), profile_b (recommended ~1.24GB), profile_c (extended ~1.44GB)",
    )
    parser.add_argument(
        "--dataset",
        nargs="+",
        help="Specific dataset IDs to download instead of profile",
    )
    args = parser.parse_args()

    profiles = dataset_settings.get_profiles()
    if args.dataset:
        target_ids = args.dataset
    else:
        target_ids = profiles.get(args.profile, {}).get("datasets", [])

    if not target_ids:
        print(f"No datasets found for profile '{args.profile}'.")
        sys.exit(1)

    success = download_datasets(target_ids)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
