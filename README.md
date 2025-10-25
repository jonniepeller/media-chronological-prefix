# media-chronological-prefix
Python 3 script to prefix all media files (photos and videos) within given folder with chronological dates based on capture date, falling back to date modified, then date created.

## NOTES:
**Only photo and video files are processed.** The script uses MIME type detection to identify and process only media files (image/* and video/*). All other files are automatically ignored.

**Already-prefixed files are detected.** If the script finds files that already have chronological prefixes (format: `YYYY-MM-DD HH:MM:SS filename.ext`), it will ask you what to do:
1. **Ignore** - Skip already-prefixed files and only process files without prefixes
2. **Add prefix anyway** - Add another date prefix to already-prefixed files
3. **Stop and quit** - Cancel the operation

## USAGE:
### Run on current directory
`python3 media_chronological_prefix.py`

### Run on a specific directory
`python3 media_chronological_prefix.py /path/to/media/folder`

### Make executable and run directly
```
chmod +x media_chronological_prefix.py
./media_chronological_prefix.py
./media_chronological_prefix.py /path/to/media/folder
```

### View help
`python3 media_chronological_prefix.py --help`

## DEPENDENCIES:
The script will attempt to install these, given consent from the user.
- PIL/Pillow: For image EXIF data extraction
- Hachoir: For video metadata extraction

## EXAMPLES:
### Process photos in current directory
`python3 media_chronological_prefix.py`

### Process videos in a specific folder
`python3 media_chronological_prefix.py ~/Videos/vacation_2024`