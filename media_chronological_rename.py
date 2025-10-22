#!/usr/bin/env python3
"""
Media Chronological Rename
Prefix all files within given folder with capture date, falling back to date modified, then date created.
"""

import os
import sys


def count_files(directory="."):
    """Count the number of files in the given directory (excluding subdirectories)."""
    try:
        items = os.listdir(directory)
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
        return len(files)
    except Exception as e:
        print(f"Error counting files: {e}")
        sys.exit(1)


def confirm_continue(file_count):
    """Ask user for confirmation before proceeding."""
    print(f"\nFound {file_count} file(s) in the current directory.")
    print(f"This script will attempt to rename {file_count} file(s).")

    while True:
        response = input("\nDo you want to continue? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            print("Operation cancelled.")
            return False
        else:
            print("Please enter 'y' or 'n'.")


def main():
    """Main function to run the media chronological rename script."""
    print("Media Chronological Rename")
    print("=" * 40)

    # Get current directory
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    # Count files
    file_count = count_files(current_dir)

    # Get user confirmation
    if not confirm_continue(file_count):
        sys.exit(0)

    print("\nProceeding with file renaming...")
    # TODO: Implement file renaming logic
    print("File renaming functionality coming soon!")


if __name__ == "__main__":
    main()
