#!/usr/bin/env python3
"""
Media Chronological Rename
See README.md for docs

TODO:
- Ask user if they want to replace prefix, or ignore files that have already been named this way—then do what they ask.
"""

import os
import sys
import argparse
from datetime import datetime
import subprocess
import mimetypes

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


def is_media_file(filepath):
    """
    Check if a file is a photo or video based on MIME type.
    Returns True if the file is image/* or video/*, False otherwise.
    """
    mime_type, _ = mimetypes.guess_type(filepath)

    if mime_type:
        return mime_type.startswith('image/') or mime_type.startswith('video/')

    return False


def get_filtered_files(directory="."):
    """
    Get list of media files (photos/videos) in the given directory.
    Returns a list of filenames (excludes subdirectories and non-media files).
    """
    items = os.listdir(directory)
    files = [item for item in items
            if os.path.isfile(os.path.join(directory, item))
            and is_media_file(os.path.join(directory, item))]
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


def confirm_continue(file_count, file_list):
    """Ask user for initial confirmation before proceeding."""
    print(f"\nFound {file_count} file(s) in the current directory.")

    # Show first up to 3 files
    if file_list:
        print("\nSample files:")
        for i, filename in enumerate(file_list[:3], 1):
            print(f"  {i}. {filename}")
        if file_count > 3:
            print(f"  ... and {file_count - 3} more")

    print(f"\nThis script will attempt to rename all {file_count} file(s).")

    return prompt_yes_no("Do you want to continue?")


def generate_new_filename(file_info, existing_names):
    """
    Generate a new filename with date prefix.
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
    print("\n" + "=" * 60)
    print("WARNING: Files with Missing Capture Dates")
    print("=" * 60)
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

    return prompt_yes_no("Do you want to continue with renaming?")


def preview_renames(files_data):
    """
    Show a preview of the renames and ask for final confirmation.
    Returns True to continue, False to cancel.
    """
    print("\n" + "=" * 60)
    print("Preview of Renaming")
    print("=" * 60)
    print("\nShowing first up to 5 renames:\n")

    for i, file_info in enumerate(files_data[:5], 1):
        print(f"{i}. {file_info['filename']}")
        print(f"   → {file_info['new_filename']}")
        print()

    if len(files_data) > 5:
        print(f"... and {len(files_data) - 5} more files will be renamed")

    print(f"\nTotal files to rename: {len(files_data)}")

    return prompt_yes_no("Proceed with renaming?")


def rename_files(files_data, target_dir):
    """
    Perform the actual file renaming.
    Returns count of successfully renamed files.
    """
    renamed_count = 0
    errors = []

    print("\nRenaming files...")

    for file_info in files_data:
        old_path = file_info['original_path']
        new_path = os.path.join(target_dir, file_info['new_filename'])

        try:
            os.rename(old_path, new_path)
            renamed_count += 1
        except Exception as e:
            errors.append((file_info['filename'], str(e)))

    # Display results
    print("\n" + "=" * 60)
    print("Renaming Complete")
    print("=" * 60)
    print(f"\nSuccessfully renamed: {renamed_count}/{len(files_data)} files")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for filename, error in errors[:5]:
            print(f"  - {filename}: {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")

    return renamed_count


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

    # Get list of files
    file_list = get_file_list(target_dir)
    file_count = len(file_list)

    # Get user confirmation
    if not confirm_continue(file_count, file_list):
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

    # Check for missing capture dates and confirm
    if not confirm_missing_capture_dates(files_data):
        sys.exit(0)

    # Generate new filenames
    print("\nGenerating new filenames...")
    existing_names = set()
    for file_info in files_data:
        new_filename = generate_new_filename(file_info, existing_names)
        file_info['new_filename'] = new_filename
        existing_names.add(new_filename)

    # Preview renames and get final confirmation
    if not preview_renames(files_data):
        sys.exit(0)

    # Perform the renaming
    rename_files(files_data, target_dir)


if __name__ == "__main__":
    main()
