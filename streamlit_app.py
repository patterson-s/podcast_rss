from __future__ import annotations
import json
import streamlit as st
import re
import zipfile
import io
from app.resolvers.orchestrator import find_feed  # absolute import works from root
from app.parser.rss_parser import PodcastRSSParser  # new parser module
from app.http import get  # Import the HTTP utility for downloads

st.set_page_config(page_title="Get RSS Feed (Open Source)", page_icon="📻")

st.title("Get RSS Feed (Open Source)")
st.caption("Paste a podcast page URL or type a show title. Returns the canonical RSS feed if it exists.")

# Initialize session state
if 'current_feed_url' not in st.session_state:
    st.session_state.current_feed_url = None
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None

with st.form("resolver"):
    user_input = st.text_input(
        "Apple/Spotify/Publisher URL — or a show title",
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
        # Show episodes in a data table
        episodes_df = []
        for i, ep in enumerate(episodes[:10]):  # Show first 10
            episodes_df.append({
                'Episode': i + 1,
                'Title': ep['title'][:50] + '...' if ep['title'] and len(ep['title']) > 50 else ep['title'],
                'Date': ep['pub_date_clean'][:10] if ep['pub_date_clean'] else 'N/A',
                'Duration': ep['duration'] or 'N/A',
                'Audio URL': ep['audio_url'][:50] + '...' if ep['audio_url'] else 'N/A'
            })
        
        st.dataframe(episodes_df, use_container_width=True)
        
        if len(episodes) > 10:
            st.info(f"Showing first 10 of {len(episodes)} episodes")
    
    # Download options
    st.subheader("Export Options")
    
    # Audio file download section
    st.write("**Download Audio Files:**")
    st.caption("Note: Large files may take several minutes to prepare for download")
    
    download_col1, download_col2 = st.columns(2)
    with download_col1:
        download_sample = st.button("Download 5 Sample Episodes", type="primary")
    with download_col2:
        download_all = st.button("Download All Episodes", type="secondary")
    
    if download_sample or download_all:
        episodes_to_download = episodes[:5] if download_sample else episodes
        
        if len(episodes_to_download) > 20 and download_all:
            st.warning(f"You're about to download {len(episodes_to_download)} episodes. This may take a very long time and create a large file. Consider downloading samples first.")
            confirm = st.button("Yes, download all episodes anyway")
            if not confirm:
                st.stop()
        
        st.info(f"Preparing download of {len(episodes_to_download)} episodes...")
        
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Create zip file in memory
        zip_buffer = io.BytesIO()
        download_results = []
        successful_downloads = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i, episode in enumerate(episodes_to_download):
                if episode['audio_url']:
                    status_text.text(f"Downloading: {episode['title'][:50]}...")
                    
                    try:
                        # Generate clean filename
                        clean_title = re.sub(r'[^\w\s-]', '', episode['title'] or 'episode')
                        clean_title = re.sub(r'[-\s]+', '_', clean_title)[:50]
                        filename = f"{i+1:02d}_{clean_title}.mp3"
                        
                        # Download the file
                        audio_response = get(episode['audio_url'])
                        audio_response.raise_for_status()
                        
                        # Add to zip
                        zip_file.writestr(filename, audio_response.content)
                        
                        download_results.append(f"✅ {episode['title']}")
                        successful_downloads += 1
                        
                    except Exception as e:
                        download_results.append(f"❌ {episode['title']}: {str(e)}")
                
                # Update progress
                progress_bar.progress((i + 1) / len(episodes_to_download))
        
        status_text.text("Download complete!")
        
        # Show download results
        st.write("**Download Results:**")
        st.write(f"Successfully downloaded: {successful_downloads}/{len(episodes_to_download)} episodes")
        
        with st.expander("View detailed results"):
            for result in download_results:
                st.write(result)
        
        # Provide zip download
        if successful_downloads > 0:
            zip_buffer.seek(0)
            podcast_name = podcast_info.get('title', 'podcast').replace(' ', '_')
            download_type = 'sample' if download_sample else 'all'
            
            st.download_button(
                label=f"📦 Download {successful_downloads} Episodes (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"{podcast_name}_{download_type}_episodes.zip",
                mime="application/zip",
                type="primary"
            )
            
            # Calculate approximate file size
            zip_size_mb = len(zip_buffer.getvalue()) / (1024 * 1024)
            st.caption(f"Zip file size: ~{zip_size_mb:.1f} MB")
        
        else:
            st.error("No episodes were successfully downloaded.")
    
    # Clear downloads button
    if st.button("🗑️ Clear Downloaded Files"):
        if 'downloaded_files' in st.session_state:
            del st.session_state.downloaded_files
        st.success("Cleared downloaded files from memory")
    
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
    - Spotify resolution uses public oEmbed → title match via Apple.  
    - Generic pages use HTML autodiscovery with validation.  
    - RSS parsing extracts all episode metadata and audio download links.
    """
)