#!/usr/bin/env python3
"""
Media Chronological Rename
Prefix all files within given folder with capture date, falling back to date modified, then date created.

USAGE:
    # Run on current directory
    python3 media_chronological_rename.py

    # Run on a specific directory
    python3 media_chronological_rename.py /path/to/media/folder

    # Make executable and run directly
    chmod +x media_chronological_rename.py
    ./media_chronological_rename.py
    ./media_chronological_rename.py /path/to/media/folder

    # View help
    python3 media_chronological_rename.py --help

DEPENDENCIES:
    Required:
    - PIL/Pillow: For image EXIF data extraction
    - Hachoir: For video metadata extraction

    Installation (automatic on first run, or manual):
    pip install Pillow hachoir

EXAMPLES:
    # Process photos in current directory
    python3 media_chronological_rename.py

    # Process videos in a specific folder
    python3 media_chronological_rename.py ~/Videos/vacation_2024
"""

import os
import sys
import argparse
from datetime import datetime
import subprocess

# Check for required dependencies
MISSING_DEPS = []

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    MISSING_DEPS.append('Pillow')
    Image = None
    TAGS = None

try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
except ImportError:
    MISSING_DEPS.append('hachoir')
    createParser = None
    extractMetadata = None


def check_dependencies():
    """
    Check if required dependencies are installed and offer to install them.
    Returns True if all required dependencies are available, False otherwise.
    """
    if not MISSING_DEPS:
        return True

    print("\n" + "=" * 50)
    print("MISSING REQUIRED DEPENDENCIES")
    print("=" * 50)
    print("\nThe following required packages are not installed:")
    for dep in MISSING_DEPS:
        print(f"  - {dep}")

    print("\nTo run this script, you need to install the missing packages.")

    while True:
        response = input("\nWould you like to install them now? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return install_dependencies()
        elif response in ['n', 'no']:
            print("\nPlease install the dependencies manually:")
            print(f"  pip install {' '.join(MISSING_DEPS)}")
            return False
        else:
            print("Please enter 'y' or 'n'.")


def install_dependencies():
    """
    Attempt to install missing dependencies using pip.
    Returns True if successful, False otherwise.
    """
    print("\nAttempting to install missing dependencies...")

    try:
        for dep in MISSING_DEPS:
            print(f"\nInstalling {dep}...")
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', dep],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"  ✓ {dep} installed successfully")
            else:
                print(f"  ✗ Failed to install {dep}")
                print(f"  Error: {result.stderr}")
                return False

        print("\n" + "=" * 50)
        print("All dependencies installed successfully!")
        print("Please restart the script to use the newly installed packages.")
        print("=" * 50)
        return False  # Return False so script exits and user restarts it

    except Exception as e:
        print(f"\nError during installation: {e}")
        print("\nPlease install the dependencies manually:")
        print(f"  pip install {' '.join(MISSING_DEPS)}")
        return False


def get_capture_date(filepath):
    """
    Extract the capture date from EXIF/metadata of image or video files.
    Returns datetime object if found, None otherwise.
    Tries multiple methods:
    1. PIL/Pillow for images (JPEG, PNG, etc.)
    2. Hachoir for videos and other media files
    """
    # Try PIL for images first
    try:
        image = Image.open(filepath)
        exif_data = image._getexif()

        if exif_data is not None:
            # Look for DateTimeOriginal (when photo was taken)
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    # EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        pass  # Not an image or PIL failed, try hachoir

    # Try hachoir for videos and other media files
    if createParser is not None:
        try:
            parser = createParser(filepath)
            if parser:
                metadata = extractMetadata(parser)
                if metadata:
                    # Try to get creation date
                    creation_date = metadata.get('creation_date')
                    if creation_date:
                        return creation_date
                parser.stream._input.close()
        except Exception:
            pass  # Hachoir failed

    return None


def count_files(directory="."):
    """Count the number of files in the given directory (excluding subdirectories)."""
    try:
        items = os.listdir(directory)
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]
        return len(files)
    except Exception as e:
        print(f"Error counting files: {e}")
        sys.exit(1)


def get_file_metadata(directory="."):
    """
    Get metadata for all files in the directory.
    Returns a list of dictionaries with file information.
    """
    files_data = []

    try:
        items = os.listdir(directory)
        files = [item for item in items if os.path.isfile(os.path.join(directory, item))]

        for filename in files:
            filepath = os.path.join(directory, filename)

            # Get file stats
            stat_info = os.stat(filepath)
            modified_date = datetime.fromtimestamp(stat_info.st_mtime)
            created_date = datetime.fromtimestamp(stat_info.st_ctime)

            # Try to get capture date from EXIF/metadata
            capture_date = get_capture_date(filepath)

            # Determine final date using fallback logic
            final_date = capture_date or modified_date or created_date

            # Create file data dictionary
            file_info = {
                'original_path': filepath,
                'filename': filename,
                'modified_date': modified_date,
                'created_date': created_date,
                'capture_date': capture_date,
                'final_date': final_date,
                'new_filename': None
            }

            files_data.append(file_info)

        return files_data

    except Exception as e:
        print(f"Error getting file metadata: {e}")
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Rename media files with chronological prefixes based on capture date—if this isn't available, fallback to modified, then created dates."
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory path to process (defaults to current directory)'
    )
    args = parser.parse_args()

    print("Media Chronological Rename")
    print("=" * 40)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Get target directory
    target_dir = os.path.abspath(args.path)

    # Validate directory exists
    if not os.path.isdir(target_dir):
        print(f"Error: '{args.path}' is not a valid directory.")
        sys.exit(1)

    # Inform user about the target directory
    if args.path == '.':
        print(f"No path provided. Using current directory: {target_dir}")
    else:
        print(f"Target directory: {target_dir}")

    # Count files
    file_count = count_files(target_dir)

    # Get user confirmation
    if not confirm_continue(file_count):
        sys.exit(0)

    print("\nProceeding with file renaming...")

    # Get file metadata
    print("Collecting file metadata...")
    files_data = get_file_metadata(target_dir)

    # Display sample data
    print(f"\nCollected metadata for {len(files_data)} file(s).")
    if files_data:
        print("\nSample file data:")
        sample = files_data[0]
        print(f"  Filename: {sample['filename']}")
        print(f"  Path: {sample['original_path']}")
        print(f"  Capture Date: {sample['capture_date'] if sample['capture_date'] else 'Not found'}")
        print(f"  Modified Date: {sample['modified_date']}")
        print(f"  Created Date: {sample['created_date']}")
        print(f"  Final Date (for renaming): {sample['final_date']}")

    # TODO: Generate new filenames and perform rename
    print("\nFile renaming functionality coming soon!")


if __name__ == "__main__":
    main()
