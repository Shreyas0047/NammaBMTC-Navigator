#!/usr/bin/env python3
"""
Fetch and extract the candidate BMTC GTFS dataset from Vonter/bmtc-gtfs.
"""

import os
import sys
import urllib.request
import zipfile

GTFS_URL = "https://raw.githubusercontent.com/Vonter/bmtc-gtfs/main/gtfs/bmtc.zip"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
GTFS_DIR = os.path.join(BASE_DIR, "data", "gtfs")
ZIP_PATH = os.path.join(RAW_DIR, "bmtc.zip")


def report_progress(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\rDownloading: {percent:.1f}% ({mb_down:.1f}MB / {mb_total:.1f}MB)")
        sys.stdout.flush()


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(GTFS_DIR, exist_ok=True)

    if not os.path.exists(ZIP_PATH):
        print(f"Fetching BMTC GTFS feed from:\n  {GTFS_URL}")
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [("User-Agent", "bmtc-recommender-fetch/1.0")]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(GTFS_URL, ZIP_PATH, reporthook=report_progress)
            print("\nDownload complete.")
        except Exception as e:
            print(f"\nError downloading GTFS feed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Using cached zip archive at: {ZIP_PATH}")

    print(f"Extracting to {GTFS_DIR} ...")
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        z.extractall(GTFS_DIR)
        namelist = z.namelist()
        print(f"Successfully extracted {len(namelist)} files:")
        for name in sorted(namelist):
            info = z.getinfo(name)
            mb = info.file_size / (1024 * 1024)
            print(f"  - {name} ({mb:.2f} MB)")


if __name__ == "__main__":
    main()
