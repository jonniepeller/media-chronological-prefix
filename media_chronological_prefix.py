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


def print_heading(message):
    if(message):
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)


def check_dependencies():
    """
    Check if required dependencies are installed and offer to install them.
    Returns True if all required dependencies are available, False otherwise.
    """
    if not MISSING_DEPS:
        return True

    print_heading("MISSING REQUIRED DEPENDENCIES")
    print("\nThe following required packages are not installed:")
    for dep in MISSING_DEPS:
        print(f"  - {dep}")

    print("\nTo run this script, you need to install the missing packages.")

    if prompt_yes_no("Would you like to install them now?", cancel_message=None):
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
    Check if a file has already been prefixed with the chronological format.
    Expected format: YYYY-MM-DD HH:MM:SS[.mmm] original_name.ext
    Returns True if the filename matches the pattern, False otherwise.
    """
    # Pattern matches: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM:SS.mmm at the start
    # followed by a space and then the rest of the filename
    pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d{3})? .+'

    return bool(re.match(pattern, filename))


def get_filtered_files(directory=".", include_already_prefixed=True):
    """
    Get list of media files (photos/videos) in the given directory.
    Returns a list of filenames (excludes subdirectories and non-media files).
    If include_already_prefixed is False, excludes files already prefixed with chronological format.
    """
    items = os.listdir(directory)
    files = [item for item in items
            if os.path.isfile(os.path.join(directory, item))
            and is_media_file(os.path.join(directory, item))]

    if not include_already_prefixed:
        files = [f for f in files if not is_already_prefixed(f)]

    return files


def prompt_yes_no(question, cancel_message="Operation cancelled."):
    """
    Prompt user for yes/no confirmation.
    Returns True for yes, False for no.
    """
    while True:
        response = input(f"\n{question} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            if cancel_message:
                print(cancel_message)
            return False
        else:
            print("Please enter 'y' or 'n'.")


def get_file_list(directory="."):
    """
    Get list of media files in the given directory (photos and videos only).
    Excludes subdirectories and non-media files.
    Returns a list of filenames.
    """
    try:
        return get_filtered_files(directory)
    except Exception as e:
        print(f"Error listing files: {e}")
        sys.exit(1)


def get_file_metadata(directory="."):
    """
    Get metadata for all media files in the directory (photos and videos only).
    Excludes non-media files.
    Returns a list of dictionaries with file information.
    """
    files_data = []

    try:
        files = get_filtered_files(directory)

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


def confirm_already_prefixed_files(already_prefixed_files):
    """
    Check for files already prefixed with chronological format and ask user what to do.
    Returns: 'ignore', 'prefix_anyway', or 'quit'
    """
    if not already_prefixed_files:
        return 'ignore'  # No already-prefixed files, proceed normally

    print_heading("WARNING: Already-Prefixed Files Detected")
    print(f"\n{len(already_prefixed_files)} file(s) already have chronological prefixes.")
    print("These files appear to have already been processed by this script.\n")

    # Show first up to 5 already-prefixed files
    print("Already-prefixed files:")
    for i, filename in enumerate(already_prefixed_files[:5], 1):
        print(f"  {i}. {filename}")

    if len(already_prefixed_files) > 5:
        print(f"  ... and {len(already_prefixed_files) - 5} more")

    print("\nWhat would you like to do?")
    print("  1. Ignore these files (only prefix files without chronological prefix)")
    print("  2. Add prefix anyway (will add another date prefix)")
    print("  3. Stop and quit")

    while True:
        response = input("\nEnter your choice (1/2/3): ").strip()
        if response == '1':
            return 'ignore'
        elif response == '2':
            return 'prefix_anyway'
        elif response == '3':
            print("Operation cancelled.")
            return 'quit'
        else:
            print("Please enter 1, 2, or 3.")


def confirm_continue(file_count, file_list):
    """Ask user for initial confirmation before proceeding."""
    print(f"\nFound {file_count} media file(s) to process.")

    # Show first up to 3 files
    if file_list:
        print("\nSample files:")
        for i, filename in enumerate(file_list[:3], 1):
            print(f"  {i}. {filename}")
        if file_count > 3:
            print(f"  ... and {file_count - 3} more")

    print(f"\nThis script will attempt to prefix {file_count} file(s) with chronological dates.")

    return prompt_yes_no("Do you want to continue?")


def generate_prefixed_filename(file_info, existing_names):
    """
    Generate a new filename with chronological date prefix.
    Format: YYYY-MM-DD HH:MM:SS original_filename.ext (24-hour time)
    Includes milliseconds if available.
    Handles collisions by adding a counter suffix.
    """
    final_date = file_info['final_date']
    original_filename = file_info['filename']

    # Format: YYYY-MM-DD HH:MM:SS (24-hour time)
    # Try to include microseconds if available
    if hasattr(final_date, 'microsecond') and final_date.microsecond > 0:
        # Convert microseconds to milliseconds (first 3 digits)
        milliseconds = final_date.microsecond // 1000
        date_prefix = final_date.strftime(f'%Y-%m-%d %H:%M:%S.{milliseconds:03d}')
    else:
        date_prefix = final_date.strftime('%Y-%m-%d %H:%M:%S')

    # Create new filename
    new_filename = f"{date_prefix} {original_filename}"

    # Handle collisions - if filename already exists, add counter
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

    # Some files are missing capture dates
    print_heading("WARNING: Files with Missing Capture Dates")
    print(f"\n{len(missing_capture)} file(s) do not have capture date metadata.")
    print("These files will use modified date or created date instead.\n")

    # Show first up to 5 files without capture dates
    print("Files without capture dates:")
    for i, file_info in enumerate(missing_capture[:5], 1):
        fallback = "modified date" if file_info['final_date'] == file_info['modified_date'] else "created date"
        print(f"  {i}. {file_info['filename']} (will use {fallback})")

    if len(missing_capture) > 5:
        print(f"  ... and {len(missing_capture) - 5} more")

    print(f"\nFiles with capture dates: {len(files_data) - len(missing_capture)}/{len(files_data)}")
    print(f"Files using fallback dates: {len(missing_capture)}/{len(files_data)}")

    return prompt_yes_no("Do you want to continue with prefixing?")

def confirm_prefixes(files_data):
    """
    Show a preview of the prefixed filenames and ask for final confirmation.
    Returns True to continue, False to cancel.
    """
    print_heading("Preview of Prefixed Filenames")
    print("\nShowing first up to 5 files:\n")

    for i, file_info in enumerate(files_data[:5], 1):
        print(f"{i}. {file_info['filename']}")
        print(f"   → {file_info['new_filename']}")
        print()

    if len(files_data) > 5:
        print(f"... and {len(files_data) - 5} more files will be prefixed")

    print(f"\nTotal files to prefix: {len(files_data)}")

    return prompt_yes_no("Proceed with prefixing?")


def prefix_files(files_data, target_dir):
    """
    Perform the actual file prefixing (renaming with date prefix).
    Returns count of successfully prefixed files.
    """
    prefixed_count = 0
    errors = []

    for file_info in files_data:
        old_path = file_info['original_path']
        new_path = os.path.join(target_dir, file_info['new_filename'])

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
        for filename, error in errors[:5]:
            print(f"  - {filename}: {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")

    return prefixed_count


def main():
    """Main function to run from the command line, in Python 3."""
    parser = argparse.ArgumentParser(
        description="Prefix media files with chronological dates based on capture date—if this isn't available, fallback to modified, then created dates."
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
    if not check_dependencies():
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
    all_files = get_filtered_files(target_dir, include_already_prefixed=True)

    # Handle any already prefixed based on user's preference
    already_prefixed = [f for f in all_files if is_already_prefixed(f)]
    prefix_choice = confirm_already_prefixed_files(already_prefixed)
    if prefix_choice == 'ignore':
        # Only process files that haven't been prefixed yet
        file_list = [f for f in all_files if not is_already_prefixed(f)]
    elif prefix_choice == 'prefix_anyway':
        # Process all files including already-prefixed ones
        file_list = all_files
    elif prefix_choice == 'quit':
        # User chose to stop
        sys.exit(0)
    else:
        # Unexpected value—Quit
        print(f"Error: Unexpected value '{prefix_choice}' returned from confirm_already_prefixed_files")
        sys.exit(1)

    file_count = len(file_list)

    # If no files to process, exit
    if file_count == 0:
        print("\nNo media files to process.")
        sys.exit(0)

    # Get user confirmation if they'd like to continue
    if not confirm_continue(file_count, file_list):
        sys.exit(0)
    print("\nOK, proceeding...")

    print("\nCollecting file metadata...")
    # Get file metadata for the selected files
    files_data = []
    try:
        for filename in file_list:
            filepath = os.path.join(target_dir, filename)

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

    except Exception as e:
        print(f"Error getting file metadata: {e}")
        sys.exit(1)

    print(f"\nCollected metadata for {len(files_data)} file(s).")

    # Check for missing capture dates and confirm
    if not confirm_missing_capture_dates(files_data):
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
        sys.exit(0)

    # Perform the prefixing
    print("\nPrefixing files...")
    prefix_files(files_data, target_dir)


if __name__ == "__main__":
    main()
