from __future__ import annotations
import json
import streamlit as st
from app.resolvers.orchestrator import find_feed  # absolute import works from root
from app.parser.rss_parser import PodcastRSSParser  # new parser module

st.set_page_config(page_title="Get RSS Feed (Open Source)", page_icon="📻")

st.title("Get RSS Feed (Open Source)")
st.caption("Paste a podcast page URL or type a show title. Returns the canonical RSS feed if it exists.")

# Initialize session state for feed URL
if 'current_feed_url' not in st.session_state:
    st.session_state.current_feed_url = None

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
                st.success(f"Successfully parsed {len(parser.episodes)} episodes")
                
                # Display podcast metadata
                st.subheader("Podcast Information")
                podcast_info = parser.podcast_metadata
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Title:** {podcast_info.get('title', 'N/A')}")
                    st.write(f"**Language:** {podcast_info.get('language', 'N/A')}")
                    st.write(f"**Category:** {podcast_info.get('category', 'N/A')}")
                with col2:
                    st.write(f"**Author:** {podcast_info.get('author', 'N/A')}")
                    st.write(f"**Total Episodes:** {len(parser.episodes)}")
                    if podcast_info.get('last_build_date'):
                        st.write(f"**Last Updated:** {podcast_info['last_build_date']}")
                
                if podcast_info.get('description'):
                    st.write(f"**Description:** {podcast_info['description'][:300]}...")
                
                # Episode data preview
                st.subheader("Episode Data Preview")
                
                if parser.episodes:
                    # Show episodes in a data table
                    episodes_df = []
                    for i, ep in enumerate(parser.episodes[:10]):  # Show first 10
                        episodes_df.append({
                            'Episode': i + 1,
                            'Title': ep['title'][:50] + '...' if ep['title'] and len(ep['title']) > 50 else ep['title'],
                            'Date': ep['pub_date_clean'][:10] if ep['pub_date_clean'] else 'N/A',
                            'Duration': ep['duration'] or 'N/A',
                            'Audio URL': ep['audio_url'][:50] + '...' if ep['audio_url'] else 'N/A'
                        })
                    
                    st.dataframe(episodes_df, use_container_width=True)
                    
                    if len(parser.episodes) > 10:
                        st.info(f"Showing first 10 of {len(parser.episodes)} episodes")
                
                # Download options
                st.subheader("Export Options")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # JSON download
                    full_data = {
                        'podcast_metadata': parser.podcast_metadata,
                        'episodes': parser.episodes,
                        'total_episodes': len(parser.episodes)
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
                    audio_urls = [ep['audio_url'] for ep in parser.episodes if ep['audio_url']]
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
                    for ep in parser.episodes:
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
                    audio_urls = [ep['audio_url'] for ep in parser.episodes if ep['audio_url']]
                    st.code(f"# Download all audio files with wget\n" + 
                            '\n'.join([f'wget "{url}"' for url in audio_urls[:3]]) + 
                            f"\n# ... and {len(audio_urls)-3} more files" if len(audio_urls) > 3 else "", 
                            language="bash")
                    
                    st.write("**RSS Feed Structure:**")
                    if parser.episodes:
                        sample_episode = parser.episodes[0]
                        st.json({k: v for k, v in sample_episode.items() if k in 
                                ['title', 'pub_date_clean', 'duration', 'audio_url', 'audio_type']})
            
            else:
                st.error("Failed to parse RSS feed. The feed may be malformed or inaccessible.")

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