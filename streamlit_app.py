from __future__ import annotations
import json
import streamlit as st
import re
import zipfile
import io
from app.resolvers.orchestrator import find_feed
from app.parser.rss_parser import PodcastRSSParser
from app.http import get
from app.transcriber import Transcriber

def parse_episode_numbers(input_str: str, max_episodes: int) -> list[int] | None:
    if not input_str or not input_str.strip():
        return None
    
    indices = set()
    parts = input_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            try:
                start, end = part.split('-')
                start_num = int(start.strip())
                end_num = int(end.strip())
                if start_num < 1 or end_num > max_episodes or start_num > end_num:
                    return None
                indices.update(range(start_num - 1, end_num))
            except:
                return None
        else:
            try:
                num = int(part)
                if num < 1 or num > max_episodes:
                    return None
                indices.add(num - 1)
            except:
                return None
    
    return sorted(list(indices))

st.set_page_config(page_title="Get RSS Feed (Open Source)", page_icon="Ã°Å¸â€œÂ»")

with st.sidebar:
    st.header("How to Use This Tool")
    
    with st.expander("Use Case 1: RSS Feed Discovery", expanded=False):
        st.markdown("""
        **Find and export podcast RSS feeds for production use.**
        
        This is useful for:
        - Finding RSS feeds from Apple Podcasts or Spotify URLs
        - Discovering feeds from publisher websites
        - Searching for podcasts by name
        - Exporting episode metadata and audio URLs
        
        **Workflow:**
        1. Enter a podcast URL or search term
        2. Click "Find RSS Feed"
        3. Click "Parse feed" to load episodes
        4. Export metadata as JSON/CSV or download audio URLs
        5. Use the RSS feed or exported URLs in your own pipeline
        
        **Production Use:** This feed discovery feature is fully functional for production workflows. Download the RSS feed URL or episode lists, then process episodes locally with your own infrastructure.
        """)
    
    with st.expander("Use Case 2: End-to-End Demonstration", expanded=False):
        st.markdown("""
        **Illustrate the complete podcast transcription pipeline.**
        
        This demonstrates our research process:
        1. RSS feed discovery
        2. Episode downloading
        3. Audio transcription
        
        **Workflow:**
        1. Find and parse a podcast RSS feed
        2. Select episodes to download (start small, 1-5 episodes)
        3. Click "Download Selected Episodes"
        4. Click "Transcribe Episodes" (uses CPU, will be slow)
        5. Download audio, transcripts, or both
        
        **Note:** This is for demonstration only. CPU-based transcription is very slow. For actual dataset generation, we used GPU-accelerated infrastructure (10-30x faster). See our [Colab notebook](https://colab.research.google.com/drive/10qucU8nBED9LA-aIZ8ViK7yR_4btqEnL?usp=sharing) for the production approach.
        """)
    
    with st.expander("Use Case 3: Quick Transcription", expanded=False):
        st.markdown("""
        **Transcribe a few podcast episodes for analysis.**
        
        **Workflow:**
        1. Find your podcast
        2. Download 1-5 episodes
        3. Transcribe them in-app
        4. Download transcripts as text files
        
        **Best for:** Transcribing small numbers of episodes when you don't have GPU infrastructure available. Not suitable for large-scale transcription.
        """)
    
    with st.expander("Tips & Limitations", expanded=False):
        st.markdown("""
        **Tips:**
        - Start with 1-3 episodes to test transcription speed
        - Use "Download Audio URLs" to get links for external processing
        - RSS discovery works for most podcasts except platform exclusives
        
        **Limitations:**
        - Transcription is CPU-based and slow (30-90 min per 30-min episode)
        - Cannot access Spotify/Apple exclusive content without RSS feeds
        - Large downloads (>20 episodes) may timeout
        - Whisper base model downloads 74 MB on first use
        """)
    
    st.divider()
    st.markdown("**[View on GitHub](#)** | **[Documentation](https://github.com/yourrepo/podcast_rss)**")

st.title("Get RSS Feed (Open Source)")
st.caption("Paste a podcast page URL or type a show title. Returns the canonical RSS feed if it exists.")

# Initialize session state
if 'current_feed_url' not in st.session_state:
    st.session_state.current_feed_url = None
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'downloaded_episodes' not in st.session_state:
    st.session_state.downloaded_episodes = None
if 'transcriptions' not in st.session_state:
    st.session_state.transcriptions = None

with st.form("resolver"):
    user_input = st.text_input(
        "Apple/Spotify/Publisher URL Ã¢â‚¬â€ or a show title",
        placeholder="https://podcasts.apple.com/gb/podcast/ukraine-the-latest/id1612424182",
    )
    submitted = st.form_submit_button("Find RSS Feed")

if submitted:
    res = find_feed(user_input)
    if res.status == "found":
        st.success("Feed found")
        st.write("**RSS feed URL:**")
        st.code(res.feed_url, language=None)
        
        # Store feed URL in session state
        st.session_state.current_feed_url = res.feed_url
            
    elif res.status == "exclusive_or_unsupported":
        st.warning(res.notes or "Exclusive or unsupported")
        st.session_state.current_feed_url = None
    elif res.status == "not_found":
        st.error(res.notes or "No feed discovered")
        st.session_state.current_feed_url = None
    else:
        st.error(res.notes or "Error")
        st.session_state.current_feed_url = None

    st.divider()
    st.subheader("Debug JSON")
    st.code(json.dumps(res.__dict__, ensure_ascii=False, indent=2), language="json")

# Handle parse button click (outside the form submission block)
if st.session_state.current_feed_url:
    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Open feed", st.session_state.current_feed_url)
    with col2:
        parse_button = st.button("Parse feed", type="secondary")
    
    if parse_button:
        with st.spinner("Parsing RSS feed..."):
            parser = PodcastRSSParser(st.session_state.current_feed_url)
            
            if parser.fetch_and_parse():
                # Store parsed data in session state
                st.session_state.parsed_data = {
                    'podcast_metadata': parser.podcast_metadata,
                    'episodes': parser.episodes
                }
                st.success(f"Successfully parsed {len(parser.episodes)} episodes")
            else:
                st.error("Failed to parse RSS feed. The feed may be malformed or inaccessible.")
                st.session_state.parsed_data = None

# Display parsed data if it exists
if st.session_state.parsed_data:
    podcast_info = st.session_state.parsed_data['podcast_metadata']
    episodes = st.session_state.parsed_data['episodes']
    
    # Display podcast metadata
    st.subheader("Podcast Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Title:** {podcast_info.get('title', 'N/A')}")
        st.write(f"**Language:** {podcast_info.get('language', 'N/A')}")
        st.write(f"**Category:** {podcast_info.get('category', 'N/A')}")
    with col2:
        st.write(f"**Author:** {podcast_info.get('author', 'N/A')}")
        st.write(f"**Total Episodes:** {len(episodes)}")
        if podcast_info.get('last_build_date'):
            st.write(f"**Last Updated:** {podcast_info['last_build_date']}")
    
    if podcast_info.get('description'):
        st.write(f"**Description:** {podcast_info['description'][:300]}...")
    
    # Episode data preview
    st.subheader("Episode Data Preview")
    
    if episodes:
        episodes_df = []
        for i, ep in enumerate(episodes):
            episodes_df.append({
                'Episode': i + 1,
                'Title': ep['title'][:50] + '...' if ep['title'] and len(ep['title']) > 50 else ep['title'],
                'Date': ep['pub_date_clean'][:10] if ep['pub_date_clean'] else 'N/A',
                'Duration': ep['duration'] or 'N/A',
                'Audio URL': ep['audio_url'][:50] + '...' if ep['audio_url'] else 'N/A'
            })
        
        st.dataframe(episodes_df, use_container_width=True, height=400)
        
        st.write("")
        st.write("**Select Episodes to Download:**")
        episode_input = st.text_input(
            "Enter episode numbers (e.g., 1,5,10-20,25)",
            key="episode_selection",
            placeholder="1,5,10-20"
        )
        st.caption(f"Available episodes: 1-{len(episodes)}")

    
    # Download options
    st.subheader("Export Options")
    
    # Audio file download section
    st.write("**Download Audio Files:**")
    st.caption("Note: Large files may take several minutes to prepare for download")
    
    download_col1, download_col2 = st.columns(2)
    with download_col1:
        download_selected = st.button("Download Selected Episodes", type="primary")
    with download_col2:
        download_all = st.button("Download All Episodes", type="secondary")
    
    if download_selected or download_all:
        if download_selected:
            episode_input = st.session_state.get('episode_selection', '')
            selected_indices = parse_episode_numbers(episode_input, len(episodes))
            
            if selected_indices is None or len(selected_indices) == 0:
                st.error("Please enter valid episode numbers (e.g., 1,5,10-20)")
                st.stop()
            
            episodes_to_download = [episodes[i] for i in selected_indices]
        else:
            episodes_to_download = episodes
        
        if len(episodes_to_download) > 20:
            st.warning(f"You're about to download {len(episodes_to_download)} episodes. This may take a very long time and create a large file.")
            confirm = st.button("Yes, download anyway")
            if not confirm:
                st.stop()
        
        st.info(f"Preparing download of {len(episodes_to_download)} episodes...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        zip_buffer = io.BytesIO()
        download_results = []
        successful_downloads = 0
        downloaded_episode_data = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, episode in enumerate(episodes_to_download):
                if episode['audio_url']:
                    status_text.text(f"Downloading: {episode['title'][:50]}...")
                    
                    try:
                        clean_title = re.sub(r'[^\w\s-]', '', episode['title'] or 'episode')
                        clean_title = re.sub(r'[-\s]+', '_', clean_title)[:50]
                        filename = f"{i+1:02d}_{clean_title}.mp3"
                        
                        audio_response = get(episode['audio_url'])
                        audio_response.raise_for_status()
                        
                        zip_file.writestr(filename, audio_response.content)
                        
                        downloaded_episode_data.append({
                            'filename': filename,
                            'title': episode['title'],
                            'audio_bytes': audio_response.content,
                            'episode_index': i
                        })
                        
                        download_results.append(f"✓ {episode['title']}")
                        successful_downloads += 1
                        
                    except Exception as e:
                        download_results.append(f"✗ {episode['title']}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(episodes_to_download))
        
        status_text.text("Download complete!")
        
        st.session_state.downloaded_episodes = {
            'episodes': downloaded_episode_data,
            'zip_buffer': zip_buffer.getvalue(),
            'podcast_name': podcast_info.get('title', 'podcast').replace(' ', '_'),
            'download_type': 'selected' if download_selected else 'all'
        }
        st.session_state.transcriptions = None
        
        st.write("**Download Results:**")
        st.write(f"Successfully downloaded: {successful_downloads}/{len(episodes_to_download)} episodes")
        
        with st.expander("View detailed results"):
            for result in download_results:
                st.write(result)
        
        if successful_downloads > 0:
            zip_size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
            
            st.download_button(
                label=f"Download {successful_downloads} Episodes (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"{st.session_state.downloaded_episodes['podcast_name']}_{st.session_state.downloaded_episodes['download_type']}_episodes.zip",
                mime="application/zip",
                type="primary"
            )
            
            st.caption(f"Zip file size: ~{zip_size_mb:.1f} MB")
        
        else:
            st.error("No episodes were successfully downloaded.")
    
    if st.session_state.downloaded_episodes and not st.session_state.transcriptions:
        st.divider()
        st.subheader("Transcription")
        st.write("**Transcribe Downloaded Episodes:**")
        st.caption("Using Whisper base model. Large episodes may take several minutes each.")
        
        if st.button("Transcribe Episodes", type="secondary"):
            episodes_data = st.session_state.downloaded_episodes['episodes']
            
            st.info(f"Starting transcription of {len(episodes_data)} episodes...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            transcriber = Transcriber(model_name="base")
            status_text.text("Loading Whisper model...")
            transcriber.load_model()
            
            transcription_results = []
            successful_transcriptions = 0
            
            for i, ep_data in enumerate(episodes_data):
                status_text.text(f"Transcribing ({i+1}/{len(episodes_data)}): {ep_data['title'][:50]}...")
                
                try:
                    transcript = transcriber.transcribe_audio_bytes(
                        ep_data['audio_bytes'],
                        ep_data['filename']
                    )
                    
                    if transcript:
                        transcription_results.append({
                            'filename': ep_data['filename'],
                            'title': ep_data['title'],
                            'transcript': transcript,
                            'status': 'success'
                        })
                        successful_transcriptions += 1
                    else:
                        transcription_results.append({
                            'filename': ep_data['filename'],
                            'title': ep_data['title'],
                            'transcript': None,
                            'status': 'failed'
                        })
                
                except Exception as e:
                    transcription_results.append({
                        'filename': ep_data['filename'],
                        'title': ep_data['title'],
                        'transcript': None,
                        'status': f'error: {str(e)}'
                    })
                
                progress_bar.progress((i + 1) / len(episodes_data))
            
            status_text.text("Transcription complete!")
            
            st.session_state.transcriptions = transcription_results
            st.rerun()
    
    if st.session_state.transcriptions:
        st.divider()
        st.subheader("Transcription Results")
        
        successful = sum(1 for t in st.session_state.transcriptions if t['status'] == 'success')
        total = len(st.session_state.transcriptions)
        
        st.write(f"**Successfully transcribed: {successful}/{total} episodes**")
        
        with st.expander("View transcription details"):
            for t in st.session_state.transcriptions:
                if t['status'] == 'success':
                    st.write(f"✓ {t['title']}")
                else:
                    st.write(f"✗ {t['title']}: {t['status']}")
        
        if 'transcript_zips' not in st.session_state:
            transcript_zip = io.BytesIO()
            with zipfile.ZipFile(transcript_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for t in st.session_state.transcriptions:
                    if t['status'] == 'success':
                        txt_filename = t['filename'].rsplit('.', 1)[0] + '.txt'
                        zf.writestr(txt_filename, t['transcript'])
            
            combined_zip = io.BytesIO()
            with zipfile.ZipFile(combined_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                audio_zip_data = io.BytesIO(st.session_state.downloaded_episodes['zip_buffer'])
                with zipfile.ZipFile(audio_zip_data, 'r') as audio_zip:
                    for name in audio_zip.namelist():
                        zf.writestr(name, audio_zip.read(name))
                
                for t in st.session_state.transcriptions:
                    if t['status'] == 'success':
                        txt_filename = t['filename'].rsplit('.', 1)[0] + '.txt'
                        zf.writestr(txt_filename, t['transcript'])
            
            st.session_state.transcript_zips = {
                'transcripts_only': transcript_zip.getvalue(),
                'combined': combined_zip.getvalue()
            }
        
        st.write("**Download Options:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="Download Audio Only (ZIP)",
                data=st.session_state.downloaded_episodes['zip_buffer'],
                file_name=f"{st.session_state.downloaded_episodes['podcast_name']}_audio.zip",
                mime="application/zip",
                type="secondary"
            )
        
        with col2:
            st.download_button(
                label="Download Transcripts Only (ZIP)",
                data=st.session_state.transcript_zips['transcripts_only'],
                file_name=f"{st.session_state.downloaded_episodes['podcast_name']}_transcripts.zip",
                mime="application/zip",
                type="secondary"
            )
        
        with col3:
            st.download_button(
                label="Download Both (ZIP)",
                data=st.session_state.transcript_zips['combined'],
                file_name=f"{st.session_state.downloaded_episodes['podcast_name']}_complete.zip",
                mime="application/zip",
                type="primary"
            )

    
    
    st.divider()
    st.subheader("Export Metadata")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON download
        full_data = {
            'podcast_metadata': podcast_info,
            'episodes': episodes,
            'total_episodes': len(episodes)
        }
        json_str = json.dumps(full_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{podcast_info.get('title', 'podcast')}_data.json",
            mime="application/json"
        )
    
    with col2:
        # Audio URLs only
        audio_urls = [ep['audio_url'] for ep in episodes if ep['audio_url']]
        urls_text = '\n'.join(audio_urls)
        st.download_button(
            label="Download Audio URLs",
            data=urls_text,
            file_name=f"{podcast_info.get('title', 'podcast')}_urls.txt",
            mime="text/plain"
        )
    
    with col3:
        # Episode metadata CSV-like format
        csv_lines = ['title,pub_date,duration,audio_url,description']
        for ep in episodes:
            # Escape commas and quotes for CSV
            title = (ep['title'] or '').replace(',', ';').replace('"', '""')
            desc = (ep['description'] or '')[:100].replace(',', ';').replace('"', '""')
            csv_lines.append(
                f'"{title}",{ep["pub_date_clean"] or ""},'
                f'{ep["duration"] or ""},{ep["audio_url"] or ""},"{desc}"'
            )
        csv_text = '\n'.join(csv_lines)
        st.download_button(
            label="Download CSV",
            data=csv_text,
            file_name=f"{podcast_info.get('title', 'podcast')}_episodes.csv",
            mime="text/csv"
        )
    
    # Technical details
    with st.expander("Technical Details"):
        st.write("**Download Commands:**")
        audio_urls = [ep['audio_url'] for ep in episodes if ep['audio_url']]
        st.code(f"# Download all audio files with wget\n" + 
                '\n'.join([f'wget "{url}"' for url in audio_urls[:3]]) + 
                f"\n# ... and {len(audio_urls)-3} more files" if len(audio_urls) > 3 else "", 
                language="bash")
        
        st.write("**RSS Feed Structure:**")
        if episodes:
            sample_episode = episodes[0]
            st.json({k: v for k, v in sample_episode.items() if k in 
                    ['title', 'pub_date_clean', 'duration', 'audio_url', 'audio_type']})

st.markdown(
    """
    ---  
    **Notes**  
    - Apple resolution uses the public Lookup/Search APIs.  
    - Spotify resolution uses public oEmbed Ã¢â€ â€™ title match via Apple.  
    - Generic pages use HTML autodiscovery with validation.  
    - RSS parsing extracts all episode metadata and audio download links.
    """
)