"""
Cleanup script for production deployment.
Removes unused files and dependencies after setup.
"""
import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Files to delete
FILES_TO_DELETE = [
    "routes.txt",  # Test file from earlier debugging
    "plan.md",  # Planning document
]

# Directories to delete
DIRS_TO_DELETE = [
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".qwen",  # AI assistant cache
]

# Egg-info to delete
EGG_INFO_DIRS = [
    "world_cup_autoposter.egg-info",
]

# Development-only files (keep in dev, delete in prod)
DEV_FILES = [
    ".env.example",  # Keep example but can remove in prod
]


def delete_files(file_list, description):
    """Delete files from project root."""
    print(f"\n{description}:")
    deleted = 0
    for file_name in file_list:
        file_path = PROJECT_ROOT / file_name
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
                print(f"  ✓ Deleted: {file_name}")
                deleted += 1
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                print(f"  ✓ Deleted directory: {file_name}")
                deleted += 1
        else:
            print(f"  - Not found: {file_name}")
    return deleted


def delete_directories(dir_list, description):
    """Delete directories recursively."""
    print(f"\n{description}:")
    deleted = 0
    for dir_name in dir_list:
        for dir_path in PROJECT_ROOT.rglob(dir_name):
            if dir_path.is_dir():
                try:
                    shutil.rmtree(dir_path)
                    print(f"  ✓ Deleted: {dir_path.relative_to(PROJECT_ROOT)}")
                    deleted += 1
                except Exception as e:
                    print(f"  ✗ Failed to delete {dir_path}: {e}")
    return deleted


def main():
    """Run cleanup."""
    print("=" * 60)
    print("🧹 World Cup Autoposter Cleanup Script")
    print("=" * 60)
    
    total_deleted = 0
    
    # Delete specific files
    total_deleted += delete_files(FILES_TO_DELETE, "📄 Unused Files")
    
    # Delete directories
    total_deleted += delete_directories(DIRS_TO_DELETE, "📁 Cache Directories")
    
    # Delete egg-info
    total_deleted += delete_files(EGG_INFO_DIRS, "📦 Build Artifacts")
    
    print("\n" + "=" * 60)
    print(f"✅ Cleanup complete! Removed {total_deleted} items.")
    print("=" * 60)
    
    print("\n📝 Recommended next steps:")
    print("  1. Review .gitignore to ensure cleanup targets are excluded")
    print("  2. Run: pip install -e . --upgrade (ensure dependencies)")
    print("  3. Start server: python -m uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()