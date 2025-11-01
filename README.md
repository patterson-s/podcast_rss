# Podcast RSS Feed Finder & Transcription Tool

A Streamlit application that demonstrates the complete podcast data collection pipeline: discovering RSS feeds, downloading episodes, and transcribing audio to text.

## Purpose

This tool illustrates each step of the podcast data collection process used in our research project. **It is designed for demonstration, not for use in production.** For the actual dataset generation, we used GPU-accelerated transcription infrastructure. For more information, consult with the following (colab notebook)[https://colab.research.google.com/drive/10qucU8nBED9LA-aIZ8ViK7yR_4btqEnL?usp=sharing]

## Features

### 1. RSS Feed Discovery
- **Apple Podcasts**: Extract RSS feeds from Apple Podcasts URLs using public APIs
- **Spotify**: Resolve Spotify podcast URLs to RSS feeds via oEmbed and Apple search
- **Generic Pages**: Auto-discover RSS feeds from podcast publisher websites
- **Search**: Find podcasts by title using Apple's search API

### 2. Episode Parsing
- Parse complete RSS feed metadata
- Extract episode information (title, description, audio URL, duration, etc.)
- Display episodes in searchable table format
- Export episode metadata as JSON, CSV, or plain text

### 3. Audio Download
- Download individual or bulk episodes
- Progress tracking with status updates
- Creates organized ZIP archives with cleaned filenames
- Handles errors gracefully with detailed results

### 4. Transcription
- Transcribe downloaded episodes using OpenAI's Whisper model
- Uses Whisper base model (74 MB) for reasonable speed/accuracy balance
- Progress tracking for each episode
- Flexible download options:
  - Audio files only
  - Transcripts only
  - Both audio and transcripts together


## Usage

### Finding a Podcast Feed

1. Enter a podcast URL or search term in the input field
   - Apple Podcasts URL: `https://podcasts.apple.com/...`
   - Spotify URL: `https://open.spotify.com/show/...`
   - Publisher website URL
   - Or just type a podcast name to search

2. Click "Find RSS Feed"

3. If found, click "Parse feed" to load episodes

### Downloading Episodes

1. After parsing, view the episode list in the table
2. Enter episode numbers to download (e.g., `1,5,10-20`)
3. Click "Download Selected Episodes" or "Download All Episodes"
4. Wait for download progress bar to complete
5. Click the download button to save the ZIP file

### Transcribing Episodes

1. After downloading episodes, a "Transcribe Episodes" button appears
2. Click to start transcription (Whisper model loads on first use)
3. Monitor progress as each episode transcribes
4. After completion, choose download format:
   - Audio only
   - Transcripts only
   - Both audio and transcripts

## Performance Notes

### Transcription Speed

The in-app transcription uses Whisper's base model running on CPU. Transcription will be slow. 

**For production dataset generation**, we used:
- GPU-accelerated Whisper inference (10-30x faster)
- Parallel processing across multiple GPUs


## Project Structure

```
podcast_rss/
├── streamlit_app.py          # Main Streamlit application
├── requirements.txt           # Python dependencies
├── packages.txt               # System dependencies (ffmpeg)
│
└── app/
    ├── core.py                # Core data structures
    ├── http.py                # HTTP utilities
    ├── validators.py          # Feed validation
    ├── transcriber.py         # Whisper transcription logic
    │
    ├── parser/
    │   └── rss_parser.py      # RSS feed parsing
    │
    └── resolvers/
        ├── orchestrator.py    # Main feed resolution logic
        ├── apple.py           # Apple Podcasts resolver
        ├── spotify.py         # Spotify resolver
        └── autodiscover.py    # Generic page resolver
```

## Technical Details

### Feed Resolution

- **Apple Podcasts**: Uses iTunes Lookup and Search APIs
- **Spotify**: Leverages oEmbed API to extract show title, then searches Apple for RSS feed
- **Generic Pages**: HTML autodiscovery via `<link rel="alternate">` tags and heuristic URL patterns
- **Validation**: Verifies discovered URLs actually contain RSS/Atom feeds

### RSS Parsing

- Extracts podcast-level metadata (title, description, author, artwork)
- Parses all episodes with full metadata
- Supports iTunes podcast namespace tags
- Cleans HTML from descriptions
- Normalizes publication dates to ISO format

### Transcription

- Uses OpenAI Whisper base model (74 MB)
- Saves audio to temporary files for processing
- Returns plain text transcripts (no timestamps or metadata)
- Automatic cleanup of temporary files

## Limitations

- Transcription is CPU-based and slow for demonstration purposes
- No support for Spotify/Apple exclusive podcasts without public RSS feeds
- Large episode downloads (>20) may timeout depending on network/server
- Whisper model downloads ~74 MB on first transcription

[Add your license here]

## Acknowledgments

- OpenAI Whisper for speech recognition
- Apple for public podcast APIs
- Spotify for oEmbed API
