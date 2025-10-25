#!/usr/bin/env python3
"""
Media Chronological Prefix
See README.md for docs
"""

import os
import sys
import argparse
from datetime import datetime
import subprocess
import mimetypes
import re

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

NUM_FILES_TO_PREVIEW = 3

def print_heading(message):
    if(message):
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)


def ensure_dependencies():
    """
    Check if required dependencies are installed, offer to install them, then take that action.
    Returns True if installed, False otherwise.
    """
    if not MISSING_DEPS:
        return True

    print_heading("MISSING REQUIRED DEPENDENCIES")
    print("\nThe following packages required to run this script are not installed:")
    for dep in MISSING_DEPS:
        print(f"  - {dep}")

    if prompt_yes_no("Would you like to install them now?"):
        return install_dependencies()
    else:
        print("\nPlease install the dependencies manually:")
        print(f"  pip install {' '.join(MISSING_DEPS)}")
        return False


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

        print_heading("All dependencies installed successfully!")
        print("Please restart the script to use the newly installed packages.")
        return False

    except Exception as e:
        print_heading(f"\nError during installation: {e}")
        print("\nPlease install the dependencies manually:")
        print(f"  pip install {' '.join(MISSING_DEPS)}")
        return False


def get_capture_date(filepath):
    """
    Extract capture date from images and videos.
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
                    creation_date = metadata.get('creation_date')
                    if creation_date:
                        return creation_date
                parser.stream._input.close()
        except Exception:
            pass  # Hachoir failed

    return None


def is_media_file(filepath):
    """
    Check if a file is a photo or video based on MIME type.
    Returns True if the file is image/* or video/*, False otherwise.
    """
    mime_type, _ = mimetypes.guess_type(filepath)

    if mime_type:
        return mime_type.startswith('image/') or mime_type.startswith('video/')

    return False


def is_already_prefixed(filename):
    """
    Check if a file has already been prefixed with this exact format:
        YYYY-MM-DD HH-MM-SS original_name.ext
    Returns True if it matches, False otherwise.
    """
    pattern = r'^\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2} .+'

    return bool(re.match(pattern, filename))


def get_media_files(directory, include_already_prefixed=True):
    """
    Get list of media files (photos/videos) in the given directory.
    Returns a list of fully qualified file paths (excludes subdirectories and non-media files).
    If include_already_prefixed is False, excludes files already prefixed with chronological format.
    """
    items = os.listdir(directory)
    files = [os.path.join(directory, item) for item in items
            if os.path.isfile(os.path.join(directory, item))
            and is_media_file(os.path.join(directory, item))]

    if not include_already_prefixed:
        files = [f for f in files if not is_already_prefixed(os.path.basename(f))]

    return files


def prompt_yes_no(question):
    """
    Prompt user for yes/no confirmation of given question.
    Args: question - Question to ask the user.
    Returns: True for yes, False for no.
    """
    while True:
        response = input(f"\n{question} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")


def get_file_metadata(file_paths):
    """
    Get metadata for specified files.

    Args: file_paths - List of fully qualified file paths to process
    Returns: List of dictionaries with file information
    """
    files_data = []

    try:
        for filepath in file_paths:
            filename = os.path.basename(filepath)

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


def confirm_already_prefixed_files(already_prefixed_files):
    """
    Check for files already prefixed with chronological format,
    then if any are found, ask user what to do, then return their selected preference.

    Args: already_prefixed_files - List of file paths that are already prefixed
    Returns: 'ignore', 'prefix_anyway', or 'quit'
    """
    if not already_prefixed_files:
        return 'ignore'  # No already-prefixed files, proceed normally

    print_heading("WARNING: Already-Prefixed Files Detected")
    print(f"\n{len(already_prefixed_files)} file(s) already appear to have been processed by this script.\n")

    # Show first NUM_FILES_TO_PREVIEW already-prefixed files
    print("Already-prefixed files:")
    for i, filepath in enumerate(already_prefixed_files[:NUM_FILES_TO_PREVIEW], 1):
        print(f"  {i}. {os.path.basename(filepath)}")
    if len(already_prefixed_files) > NUM_FILES_TO_PREVIEW:
        print(f"  ... and {len(already_prefixed_files) - NUM_FILES_TO_PREVIEW} more")

    print("\nWhat would you like to do?")
    print("  1. Ignore these files (only prefix files without chronological prefix)")
    print("  2. Add prefix anyway (will add another date prefix)")
    print("  3. Stop and quit")

    while True:
        response = input("\nEnter your choice (1, 2, or 3): ").strip()
        if response == '1':
            return 'ignore'
        elif response == '2':
            return 'prefix_anyway'
        elif response == '3':
            return 'quit'
        else:
            print("Please enter 1, 2, or 3.")


def confirm_continue(file_count, file_list):
    """
    Ask user for initial confirmation before proceeding.

    Args: file_count - Number of files; file_list - List of file paths
    Returns: True to continue, False to cancel
    """
    print(f"\nFound {file_count} media file(s) to process.")

    # Preview NUM_FILES_TO_PREVIEW files
    if file_list:
        print("\nSample files:")
        for i, filepath in enumerate(file_list[:NUM_FILES_TO_PREVIEW], 1):
            print(f"  {i}. {os.path.basename(filepath)}")
        if file_count > NUM_FILES_TO_PREVIEW:
            print(f"  ... and {file_count - NUM_FILES_TO_PREVIEW} more")

    print(f"\nThis script will attempt to prefix {file_count} file(s) with chronological dates.")

    return prompt_yes_no("Do you want to continue?")


def generate_prefixed_filename(file_info, existing_names):
    """
    Generate a new filename with date prefix.
    Format: YYYY-MM-DD HH-MM-SS original_filename.ext (24-hour time)
    Handles collisions by adding a counter suffix.
    """
    # Get the data
    final_date = file_info['final_date']
    original_filename = file_info['filename']

    # Make the filename
    date_prefix = final_date.strftime('%Y-%m-%d %H-%M-%S')
    new_filename = f"{date_prefix} {original_filename}"

    # Handle collisions - if filename already exists, add counter
    # Not currently possible, but if sub-directories are added, this could become an issue.
    if new_filename in existing_names:
        base_name, extension = os.path.splitext(original_filename)
        counter = 1
        while True:
            new_filename = f"{date_prefix} {base_name} ({counter}){extension}"
            if new_filename not in existing_names:
                break
            counter += 1

    return new_filename


def confirm_missing_capture_dates(files_data):
    """
    Check for files with missing capture dates and ask user for confirmation.
    Returns True to continue, False to cancel.
    """
    # Find files without capture dates
    missing_capture = [f for f in files_data if f['capture_date'] is None]

    if not missing_capture:
        # All files have capture dates
        return True

    # Some files are missing capture dates...
    # Inform the user
    print_heading("WARNING: Files with Missing Capture Dates")
    print(f"{len(missing_capture)} file(s) do not have capture date metadata.")
    print("These files will use date modified if available, otherwise date created.")

    # Show the first NUM_FILES_TO_PREVIEW files without capture dates
    print("\nFiles without capture dates:")
    for i, file_info in enumerate(missing_capture[:NUM_FILES_TO_PREVIEW], 1):
        fallback = "modified date" if file_info['final_date'] == file_info['modified_date'] else "created date"
        print(f"  {i}. {file_info['filename']} (will use {fallback})")
    if len(missing_capture) > NUM_FILES_TO_PREVIEW:
        print(f"  ... and {len(missing_capture) - NUM_FILES_TO_PREVIEW} more")

    # Ask the user what they'd like to do
    return prompt_yes_no("Do you want to continue with prefixing?")

def confirm_prefixes(files_data):
    """
    Show a preview of the prefixed filenames and ask for final confirmation.
    Returns True to continue, False to cancel.
    """
    print_heading("Preview of Prefixed Filenames")
    print(f"\nShowing first {NUM_FILES_TO_PREVIEW} files:\n")

    for i, file_info in enumerate(files_data[:NUM_FILES_TO_PREVIEW], 1):
        print(f"{i}. {file_info['filename']}")
        print(f"   → {file_info['new_filename']}")
        print()
    if len(files_data) > NUM_FILES_TO_PREVIEW:
        print(f"... and {len(files_data) - NUM_FILES_TO_PREVIEW} more files will be prefixed")

    return prompt_yes_no(f"Proceed with prefixing {len(files_data)} files?")


def prefix_files(files_data):
    """
    Perform the actual file prefixing (renaming with date prefix).

    Args: files_data - List of file info dictionaries with metadata and new filenames
    Returns: Count of successfully prefixed files
    """
    prefixed_count = 0
    errors = []

    for file_info in files_data:
        old_path = file_info['original_path']
        # Get directory from the original path
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, file_info['new_filename'])

        try:
            os.rename(old_path, new_path)
            prefixed_count += 1
        except Exception as e:
            errors.append((file_info['filename'], str(e)))

    # Display results
    print_heading("Prefixing Complete")
    print(f"\nSuccessfully prefixed: {prefixed_count}/{len(files_data)} files")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for filename, error in errors[:NUM_FILES_TO_PREVIEW]:
            print(f"  - {filename}: {error}")
        if len(errors) > NUM_FILES_TO_PREVIEW:
            print(f"  ... and {len(errors) - NUM_FILES_TO_PREVIEW} more errors")

    return prefixed_count


def main():
    """Main function to run from the command line, in Python 3."""
    parser = argparse.ArgumentParser(
        description="Prefix media files with chronological dates (YYYY-MM-DD HH-MM-SS) based on capture date—if this isn't available, fallback to modified, then created dates."
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory path to process (defaults to current directory)'
    )
    args = parser.parse_args()

    print_heading("Media Chronological Prefix")

    # Check dependencies
    print("Checking if you have the necessary libraries already installed...")
    if not ensure_dependencies():
        sys.exit(1)

    # Get and validate target directory
    print("Checking directory...")
    target_dir = os.path.abspath(args.path)
    if not os.path.isdir(target_dir):
        print(f"Error: '{args.path}' is not a valid directory.")
        sys.exit(1)

    # Inform user about the target directory
    if args.path == '.':
        print(f"No path provided. Using current directory: {target_dir}")
    else:
        print(f"Target directory: {target_dir}")

    print("Looking for and inspecting media in the given directory...")
    # Get list of ALL media files (including already-prefixed ones)
    media_files = get_media_files(target_dir, include_already_prefixed=True)

    # Handle any already prefixed based on user's preference
    already_prefixed = [f for f in media_files if is_already_prefixed(os.path.basename(f))]
    prefix_choice = confirm_already_prefixed_files(already_prefixed)
    if prefix_choice == 'ignore':
        # Only process files that haven't been prefixed yet
        media_files_filtered = [f for f in media_files if not is_already_prefixed(os.path.basename(f))]
    elif prefix_choice == 'prefix_anyway':
        # Process all files including already-prefixed ones
        media_files_filtered = media_files
    elif prefix_choice == 'quit':
        print("User opted not to continue—Quitting.")
        sys.exit(0)
    else:
        print(f"Error: Unexpected value '{prefix_choice}' returned from confirm_already_prefixed_files")
        sys.exit(1)

    media_files_filtered_count = len(media_files_filtered)

    # If no files to prefix, exit
    if media_files_filtered_count == 0:
        print("\nNo media files to prefix.")
        sys.exit(0)

    # Get user confirmation if they'd like to continue
    if not confirm_continue(media_files_filtered_count, media_files_filtered):
        print("User opted not to continue—Quitting.")
        sys.exit(0)
    print("\nOK, proceeding...")

    print("\nCollecting file metadata...")
    # Get file metadata for the selected files
    files_data = get_file_metadata(media_files_filtered)

    print(f"\nCollected metadata for {len(files_data)} file(s).")

    # Check for missing capture dates and confirm
    if not confirm_missing_capture_dates(files_data):
        print("User opted not to continue—Quitting.")
        sys.exit(0)

    # Generate new filenames with prefixes
    print("\nGenerating prefixed filenames...")
    existing_names = set()
    for file_info in files_data:
        new_filename = generate_prefixed_filename(file_info, existing_names)
        file_info['new_filename'] = new_filename
        existing_names.add(new_filename)

    # Preview prefixes and get final confirmation
    if not confirm_prefixes(files_data):
        print("User opted not to continue—Quitting.")
        sys.exit(0)

    # Perform the prefixing
    print("\nPrefixing files...")
    prefix_files(files_data)


if __name__ == "__main__":
    main()
