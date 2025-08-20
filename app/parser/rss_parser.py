from __future__ import annotations
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from ..http import get  # Use your existing HTTP utility

class PodcastRSSParser:
    def __init__(self, rss_url):
        self.rss_url = rss_url
        self.episodes = []
        self.podcast_metadata = {}
        
    def fetch_and_parse(self):
        """Fetch RSS feed and parse all episodes"""
        try:
            # Use your existing HTTP utility
            response = get(self.rss_url)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Extract podcast-level metadata
            self._extract_podcast_metadata(root)
            
            # Extract all episodes
            self._extract_episodes(root)
            
            return True
            
        except Exception as e:
            print(f"Error fetching/parsing RSS feed: {e}")
            return False
    
    def _extract_podcast_metadata(self, root):
        """Extract podcast-level information"""
        channel = root.find('channel')
        if channel is not None:
            self.podcast_metadata = {
                'title': self._get_text(channel, 'title'),
                'description': self._clean_text(self._get_text(channel, 'description')),
                'language': self._get_text(channel, 'language'),
                'link': self._get_text(channel, 'link'),
                'image_url': self._get_image_url(channel),
                'author': self._get_text(channel, 'author') or self._get_itunes_text(channel, 'author'),
                'category': self._get_category(channel),
                'last_build_date': self._get_text(channel, 'lastBuildDate'),
                'rss_url': self.rss_url
            }
    
    def _extract_episodes(self, root):
        """Extract all episode information"""
        channel = root.find('channel')
        if channel is None:
            return
            
        items = channel.findall('item')
        
        for item in items:
            episode = self._parse_episode(item)
            if episode:
                self.episodes.append(episode)
    
    def _parse_episode(self, item):
        """Parse individual episode data"""
        # Get enclosure (audio file) information
        enclosure = item.find('enclosure')
        if enclosure is None:
            return None  # Skip episodes without audio files
            
        # Extract episode metadata
        episode = {
            'title': self._clean_text(self._get_text(item, 'title')),
            'description': self._clean_text(self._get_text(item, 'description')),
            'pub_date': self._get_text(item, 'pubDate'),
            'pub_date_clean': None,  # Will be set below
            'guid': self._get_text(item, 'guid'),
            'link': self._get_text(item, 'link'),
            
            # Audio file information
            'audio_url': enclosure.get('url'),
            'audio_type': enclosure.get('type'),
            'audio_length': enclosure.get('length'),
            
            # iTunes-specific metadata
            'duration': self._get_itunes_text(item, 'duration'),
            'episode_number': self._get_itunes_text(item, 'episode'),
            'season_number': self._get_itunes_text(item, 'season'),
            'episode_type': self._get_itunes_text(item, 'episodeType'),
            'explicit': self._get_itunes_text(item, 'explicit'),
            
            # Podcast-level info for each episode
            'podcast_title': self.podcast_metadata.get('title'),
            'rss_source': self.rss_url
        }
        
        # Clean and standardize the pub_date
        episode['pub_date_clean'] = self._parse_date(episode['pub_date'])
        
        return episode
    
    def _get_text(self, element, tag):
        """Safely extract text from XML element"""
        found = element.find(tag)
        return found.text if found is not None else None
    
    def _get_itunes_text(self, element, tag):
        """Extract iTunes namespace elements"""
        # iTunes elements use the itunes namespace
        namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        found = element.find(f'.//itunes:{tag}', namespaces)
        if found is not None:
            return found.text or found.get('text')
        return None
    
    def _get_image_url(self, channel):
        """Extract podcast image URL"""
        # Try iTunes image first
        namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        itunes_image = channel.find('.//itunes:image', namespaces)
        if itunes_image is not None:
            return itunes_image.get('href')
        
        # Try standard RSS image
        image = channel.find('image')
        if image is not None:
            url_elem = image.find('url')
            if url_elem is not None:
                return url_elem.text
                
        return None
    
    def _get_category(self, channel):
        """Extract podcast category"""
        # Try iTunes category
        namespaces = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        itunes_cat = channel.find('.//itunes:category', namespaces)
        if itunes_cat is not None:
            return itunes_cat.get('text')
        
        # Try standard category
        category = channel.find('category')
        if category is not None:
            return category.text
            
        return None
    
    def _clean_text(self, text):
        """Clean HTML tags and normalize text"""
        if not text:
            return None
        
        # Remove HTML tags
        clean = re.sub('<.*?>', '', text)
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean if clean else None
    
    def _parse_date(self, date_str):
        """Parse RFC 2822 date format to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try parsing RFC 2822 format (most common in RSS)
            dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
            return dt.isoformat()
        except:
            try:
                # Try without timezone
                dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S')
                return dt.isoformat()
            except:
                # Return original if parsing fails
                return date_str