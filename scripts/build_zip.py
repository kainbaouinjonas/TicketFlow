#!/usr/bin/env python3
import os
import zipfile
import sys

def build_zip():
    # Define directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    zip_filename = "ticket_platform.zip"
    zip_filepath = os.path.join(base_dir, zip_filename)

    print(f"[*] Starting packaging process in base directory: {base_dir}")
    print(f"[*] Output ZIP destination: {zip_filepath}")

    # Exclusions patterns (skip virtual environments, git history, cache files, database states)
    exclude_dirs = {
        ".git",
        ".github",
        "venv",
        "env",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".idea",
        ".vscode",
        "node_modules",
        "chrome_data",
        "brain",
        "logs",
        "tmp",
    }
    
    exclude_files = {
        zip_filename,
        "db.sqlite3",
        ".env",
        ".DS_Store",
    }

    exclude_extensions = (
        ".pyc",
        ".pyo",
        ".pyd",
        ".zip",
        ".log",
    )

    zip_count = 0
    
    # Create the zip archive
    with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Modify dirs in-place to avoid traversing excluded subdirectories
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith(".")]

            for file in files:
                # File checks
                if file in exclude_files:
                    continue
                if file.startswith("."):
                    continue
                if any(file.endswith(ext) for ext in exclude_extensions):
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, base_dir)

                # Skip files inside hidden/excluded directories that might have bypassed filtering
                parts = rel_path.split(os.sep)
                if any(part in exclude_dirs for part in parts):
                    continue

                # Add to zip
                zipf.write(abs_path, rel_path)
                zip_count += 1

    print(f"[+] Zip creation completed successfully!")
    print(f"[+] Total files archived: {zip_count}")
    print(f"[+] Final ZIP File Size: {os.path.getsize(zip_filepath) / (1024 * 1024):.2f} MB")

if __name__ == "__main__":
    try:
        build_zip()
        sys.exit(0)
    except Exception as e:
        print(f"[-] Error occurred during packaging: {e}")
        sys.exit(1)
