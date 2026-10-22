import json
import logging
import re
import urllib.request

logger = logging.getLogger(__name__)


def extract_youtube_video_id(url_or_id):
    """Extracts standard 11-char YouTube video ID from various URL formats."""
    if not url_or_id:
        return None
    match = re.search(r'(?:v=|\/vi\/|youtu\.be\/|\/embed\/|\/shorts\/|\/v\/|^)([0-9A-Za-z_-]{11})(?:[&\/\?#]|$)', url_or_id)
    if match:
        return match.group(1)
    return None


def parse_timestamp_lines(text):
    """
    Parses a multiline string of timestamps and labels.
    Supports formats like:
      00:00 Intro
      01:30 - Setup and Installation
      1:02:15 Advanced Concepts
    """
    results = []
    seen = set()
    pattern = re.compile(
        r'(?:^|[\r\n])\s*(?:(?P<hours>\d{1,2}):)?(?P<mins>\d{1,2}):(?P<secs>\d{2})\s*[-–—:]?\s*(?P<title>[^\r\n]+)'
    )
    for m in pattern.finditer(text):
        h = int(m.group('hours') or 0)
        mins = int(m.group('mins'))
        s = int(m.group('secs'))
        title = m.group('title').strip()
        sec = h * 3600 + mins * 60 + s
        if sec not in seen and title:
            seen.add(sec)
            results.append({'time_seconds': sec, 'label': title})

    results.sort(key=lambda x: x['time_seconds'])
    return results


def extract_youtube_chapters(video_url_or_id):
    """
    Fetches the YouTube video page and extracts official chapters created by the YouTuber.
    Looks inside ytInitialData chapterRenderer / macroMarkersListItemRenderer,
    with a fallback parser for timestamps inside the video description.
    """
    video_id = extract_youtube_video_id(video_url_or_id)
    if not video_id:
        return []

    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            html = response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"Unable to fetch YouTube video metadata for {video_id}: {e}")
        return []

    chapters = []
    seen_seconds = set()

    # Strategy 1: Check ytInitialData structured chapters (Official YouTuber Chapters)
    data_match = re.search(r'var ytInitialData = ({.*?});</script>', html)
    if data_match:
        try:
            data = json.loads(data_match.group(1))

            def search_renderer(obj):
                if isinstance(obj, dict):
                    if 'chapterRenderer' in obj:
                        rend = obj['chapterRenderer']
                        title = rend.get('title', {}).get('simpleText', '')
                        start_ms = rend.get('timeRangeStartMillis', 0)
                        sec = int(start_ms) // 1000
                        if sec not in seen_seconds and title:
                            seen_seconds.add(sec)
                            chapters.append({'time_seconds': sec, 'label': title.strip()})
                    elif 'macroMarkersListItemRenderer' in obj:
                        rend = obj['macroMarkersListItemRenderer']
                        title = rend.get('title', {}).get('simpleText', '')
                        time_str = rend.get('timeDescription', {}).get('simpleText', '')
                        if time_str and title:
                            parts = time_str.split(':')
                            sec = 0
                            if len(parts) == 2:
                                sec = int(parts[0]) * 60 + int(parts[1])
                            elif len(parts) == 3:
                                sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                            if sec not in seen_seconds:
                                seen_seconds.add(sec)
                                chapters.append({'time_seconds': sec, 'label': title.strip()})
                    for v in obj.values():
                        search_renderer(v)
                elif isinstance(obj, list):
                    for item in obj:
                        search_renderer(item)

            search_renderer(data)
        except Exception as e:
            logger.debug(f"ytInitialData parse error: {e}")

    # Strategy 2: Fallback to description timestamps if no structured chapters
    if not chapters:
        chapters = parse_timestamp_lines(html)

    chapters.sort(key=lambda x: x['time_seconds'])
    return chapters

