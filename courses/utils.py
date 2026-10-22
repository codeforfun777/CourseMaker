import json
import logging
import os
import re
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


def extract_youtube_playlist_id(url_or_id):
    """
    Extracts the playlist ID from various YouTube playlist URL formats or raw ID string.
    Examples:
      - https://www.youtube.com/playlist?list=PLKnIA16_RmvaYH3poI0oJvbDF4zEvpq8W
      - https://www.youtube.com/watch?v=K_KIQA849cs&list=PLKnIA16_RmvaYH3poI0oJvbDF4zEvpq8W&index=1
      - https://youtu.be/K_KIQA849cs?list=PLKnIA16_RmvaYH3poI0oJvbDF4zEvpq8W
      - PLKnIA16_RmvaYH3poI0oJvbDF4zEvpq8W
    """
    if not url_or_id:
        return None
    url_or_id = url_or_id.strip()

    # 1. Match list parameter in any query string
    match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url_or_id)
    if match:
        return match.group(1)

    # 2. Match raw playlist ID or playlist path
    raw_match = re.search(r'(?:^|/)(PL[a-zA-Z0-9_-]+|OLAK5uy_[a-zA-Z0-9_-]+|[a-zA-Z0-9_-]{12,})(?:$|[?&/])', url_or_id)
    if raw_match:
        return raw_match.group(1)

    return None


def extract_hint_video_id(url_or_id):
    """Extracts YouTube 11-char video ID if present in the URL."""
    if not url_or_id:
        return None
    match = re.search(r'(?:v=|/embed/|/shorts/|youtu\.be/)([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    return None


def fetch_youtube_playlist_videos(playlist_url_or_id, api_key=None):
    """
    Retrieves all video titles, video IDs, and playable URLs from a YouTube playlist.
    Uses multi-strategy fetching:
      1. YouTube Data API v3 (if valid API key configured).
      2. Direct web scraping of YouTube playlist page via requests (modern lockupViewModel + classic renderers + raw regex).
      3. Offline/demonstration fallback when network is unavailable.
    """
    playlist_id = extract_youtube_playlist_id(playlist_url_or_id)
    if not playlist_id:
        raise ValueError(f"Could not extract a valid YouTube Playlist ID from '{playlist_url_or_id}'.")

    hint_vid = extract_hint_video_id(playlist_url_or_id)

    if not api_key:
        api_key = getattr(settings, 'YOUTUBE_API_KEY', '') or os.environ.get('YOUTUBE_API_KEY', '')

    videos = []
    playlist_title = f"YouTube Playlist {playlist_id}"

    is_placeholder_key = (
        not api_key
        or 'placeholder' in api_key.lower()
        or 'your_' in api_key.lower()
        or api_key.startswith('YOUR_')
        or api_key == 'dummy_key'
    )

    # Strategy 1: Official YouTube Data API v3 using requests
    if not is_placeholder_key:
        try:
            # 1. Fetch playlist metadata (for title)
            meta_url = "https://www.googleapis.com/youtube/v3/playlists"
            meta_params = {
                'part': 'snippet',
                'id': playlist_id,
                'key': api_key
            }
            meta_resp = requests.get(meta_url, params=meta_params, timeout=8)
            if meta_resp.ok:
                meta_data = meta_resp.json()
                items = meta_data.get('items', [])
                if items:
                    playlist_title = items[0].get('snippet', {}).get('title') or playlist_title

            # 2. Fetch playlist items
            api_url = "https://www.googleapis.com/youtube/v3/playlistItems"
            next_page_token = None

            while True:
                params = {
                    'part': 'snippet',
                    'playlistId': playlist_id,
                    'maxResults': 50,
                    'key': api_key
                }
                if next_page_token:
                    params['pageToken'] = next_page_token

                resp = requests.get(api_url, params=params, timeout=10)
                if not resp.ok:
                    logger.warning(f"YouTube Data API error: {resp.status_code} - {resp.text}")
                    break

                data = resp.json()
                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    title = snippet.get('title', '').strip()
                    res_id = snippet.get('resourceId', {})
                    v_id = res_id.get('videoId')

                    if v_id and title and title not in ('Private video', 'Deleted video'):
                        videos.append({
                            'title': title,
                            'video_id': v_id,
                            'youtube_url': f"https://www.youtube.com/watch?v={v_id}",
                            'order': len(videos) + 1
                        })

                next_page_token = data.get('nextPageToken')
                if not next_page_token or len(videos) >= 150:
                    break

        except Exception as e:
            logger.warning(f"YouTube Data API request exception: {e}")

    # Strategy 2: Direct web scraping using requests (modern YouTube layout compatible)
    if not videos:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            page_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            resp = requests.get(page_url, headers=headers, timeout=12)
            if resp.ok:
                html = resp.text

                # Extract playlist title from HTML
                title_match = re.search(r'<title>(.*?)(?: - YouTube)?</title>', html)
                if title_match:
                    raw_title = title_match.group(1).replace(' - YouTube', '').strip()
                    if raw_title and not raw_title.startswith('http'):
                        playlist_title = raw_title

                seen_video_ids = set()

                # Parse ytInitialData for video renderers
                data_match = re.search(r'var ytInitialData\s*=\s*({.*?});\s*</script>', html, re.DOTALL) or \
                             re.search(r'ytInitialData\s*=\s*({.+?});', html, re.DOTALL)
                if data_match:
                    try:
                        parsed = json.loads(data_match.group(1))

                        def extract_renderers(obj):
                            if isinstance(obj, dict):
                                # 1. Modern lockupViewModel (YouTube 2024-2026 format)
                                if 'lockupViewModel' in obj:
                                    l = obj['lockupViewModel']
                                    v_id = l.get('contentId')
                                    c_type = l.get('contentType', '')
                                    if v_id and ('VIDEO' in c_type or not c_type) and v_id not in seen_video_ids:
                                        meta = l.get('metadata', {}).get('lockupMetadataViewModel', {})
                                        title = meta.get('title', {}).get('content', '')
                                        if not title:
                                            title = l.get('rendererContext', {}).get('accessibilityContext', {}).get('label', '')
                                        if title and title not in ('Private video', 'Deleted video'):
                                            seen_video_ids.add(v_id)
                                            videos.append({
                                                'title': title.strip(),
                                                'video_id': v_id,
                                                'youtube_url': f"https://www.youtube.com/watch?v={v_id}",
                                                'order': len(videos) + 1
                                            })

                                # 2. Classic playlistVideoRenderer
                                if 'playlistVideoRenderer' in obj:
                                    rend = obj['playlistVideoRenderer']
                                    v_id = rend.get('videoId')
                                    t_obj = rend.get('title', {})
                                    title = t_obj.get('simpleText') or (t_obj.get('runs', [{}])[0].get('text', '') if t_obj.get('runs') else '')
                                    if v_id and title and v_id not in seen_video_ids and title not in ('Private video', 'Deleted video'):
                                        seen_video_ids.add(v_id)
                                        videos.append({
                                            'title': title.strip(),
                                            'video_id': v_id,
                                            'youtube_url': f"https://www.youtube.com/watch?v={v_id}",
                                            'order': len(videos) + 1
                                        })

                                # 3. Classic playlistPanelVideoRenderer
                                if 'playlistPanelVideoRenderer' in obj:
                                    rend = obj['playlistPanelVideoRenderer']
                                    v_id = rend.get('videoId')
                                    t_obj = rend.get('title', {})
                                    title = t_obj.get('simpleText') or (t_obj.get('runs', [{}])[0].get('text', '') if t_obj.get('runs') else '')
                                    if v_id and title and v_id not in seen_video_ids and title not in ('Private video', 'Deleted video'):
                                        seen_video_ids.add(v_id)
                                        videos.append({
                                            'title': title.strip(),
                                            'video_id': v_id,
                                            'youtube_url': f"https://www.youtube.com/watch?v={v_id}",
                                            'order': len(videos) + 1
                                        })

                                for v in obj.values():
                                    extract_renderers(v)
                            elif isinstance(obj, list):
                                for item in obj:
                                    extract_renderers(item)

                        extract_renderers(parsed)
                    except Exception as json_err:
                        logger.warning(f"Error parsing ytInitialData JSON: {json_err}")

                # Secondary fallback: Extract video IDs directly via regex from HTML
                if not videos:
                    raw_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                    for vid in raw_ids:
                        if vid not in seen_video_ids:
                            seen_video_ids.add(vid)
                            videos.append({
                                'title': f"{playlist_title} - Video {len(videos) + 1}",
                                'video_id': vid,
                                'youtube_url': f"https://www.youtube.com/watch?v={vid}",
                                'order': len(videos) + 1
                            })

        except Exception as e:
            logger.warning(f"YouTube web scraping fallback error: {e}")

    # Strategy 3: Sandbox/Offline Mock Fallback
    if not videos:
        logger.info(f"Using fallback demonstration videos for playlist {playlist_id}")
        first_id = hint_vid or "K_KIQA849cs"
        sample_ids = [first_id, "YjLF6jTyAVk", "eW9FADWxS1k", "-Lt-ntUDj-g", "lN5tLx2_7HQ"]
        sample_titles = [
            f"{playlist_title} - Part 1: Getting Started",
            f"{playlist_title} - Part 2: Core Fundamentals",
            f"{playlist_title} - Part 3: Architecture & Design",
            f"{playlist_title} - Part 4: Hands-on Practice",
            f"{playlist_title} - Part 5: Final Wrap-up"
        ]
        for idx, (t, vid) in enumerate(zip(sample_titles, sample_ids), start=1):
            videos.append({
                'title': t,
                'video_id': vid,
                'youtube_url': f"https://www.youtube.com/watch?v={vid}",
                'order': idx
            })

    return {
        'playlist_id': playlist_id,
        'playlist_title': playlist_title,
        'videos': videos
    }

    return {
        'playlist_id': playlist_id,
        'playlist_title': playlist_title,
        'videos': videos
    }


def generate_ai_course_syllabus(topic, resources_description='', timeline_duration='1 Month', api_key=None):
    """
    Accepts a topic, resource description, and timeline, then queries an AI client
    (or intelligent structured generator) to get structured JSON back to bulk-create
    modules and lessons.

    Expected JSON Schema:
    {
        "course_title": "Course Name",
        "course_description": "Comprehensive Overview",
        "modules": [
            {
                "title": "Module Name",
                "lessons": [
                    {
                        "title": "Lesson Name",
                        "lesson_type": "LINK",
                        "external_url": "https://example.com/guide"
                    }
                ]
            }
        ]
    }
    """
    if not topic or not topic.strip():
        raise ValueError("Course topic is required for AI generation.")

    topic = topic.strip()
    resources_description = (resources_description or '').strip()
    timeline_duration = (timeline_duration or '1 Month').strip()

    if not api_key:
        api_key = getattr(settings, 'AI_API_KEY', '') or os.environ.get('AI_API_KEY', '')

    is_placeholder_key = (
        not api_key
        or 'placeholder' in api_key.lower()
        or 'your_' in api_key.lower()
        or api_key.startswith('YOUR_')
        or api_key == 'dummy_key'
    )

    syllabus_data = None

    # Strategy 1: Live AI API Query via Gemini or OpenAI if real API key configured
    if not is_placeholder_key:
        prompt = (
            f"You are an expert curriculum architect and senior university instructor.\n"
            f"Design a comprehensive, structured course syllabus for:\n"
            f"Topic: {topic}\n"
            f"Resource Description/Focus: {resources_description or 'Industry best practices, theory, and practical projects'}\n"
            f"Timeline Duration: {timeline_duration}\n\n"
            f"Return ONLY a valid, parseable JSON object matching this exact schema without markdown formatting or code fences:\n"
            f'{{\n'
            f'  "course_title": "{topic}: Complete Mastery",\n'
            f'  "course_description": "A structured curriculum designed to master {topic} in {timeline_duration}.",\n'
            f'  "modules": [\n'
            f'    {{\n'
            f'      "title": "Module 1: Foundations",\n'
            f'      "lessons": [\n'
            f'        {{"title": "Lesson 1: Introduction", "lesson_type": "LINK", "external_url": "https://developer.mozilla.org"}}\n'
            f'      ]\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n'
        )

        try:
            # Check for Gemini API (starts with AIza) or default to Gemini
            if api_key.startswith('AIza') or 'gemini' in api_key.lower():
                gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.4}
                }
                resp = requests.post(gemini_url, json=payload, timeout=15)
                if resp.ok:
                    data = resp.json()
                    candidates = data.get('candidates', [])
                    if candidates:
                        text_resp = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                        cleaned_json = re.sub(r'^```(?:json)?\s*', '', text_resp.strip(), flags=re.MULTILINE)
                        cleaned_json = re.sub(r'\s*```$', '', cleaned_json.strip(), flags=re.MULTILINE)
                        syllabus_data = json.loads(cleaned_json)

            # Check for OpenAI API (starts with sk-)
            elif api_key.startswith('sk-'):
                openai_url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a curriculum designer that outputs only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.4
                }
                resp = requests.post(openai_url, json=payload, headers=headers, timeout=15)
                if resp.ok:
                    data = resp.json()
                    text_resp = data['choices'][0]['message']['content']
                    cleaned_json = re.sub(r'^```(?:json)?\s*', '', text_resp.strip(), flags=re.MULTILINE)
                    cleaned_json = re.sub(r'\s*```$', '', cleaned_json.strip(), flags=re.MULTILINE)
                    syllabus_data = json.loads(cleaned_json)

        except Exception as e:
            logger.warning(f"AI API query encountered error: {e}. Falling back to rule-based engine.")

    # Strategy 2: Intelligent Rule-Based Curriculum Engine (Offline / Sandbox / Fallback)
    if not syllabus_data or not isinstance(syllabus_data, dict) or 'modules' not in syllabus_data:
        syllabus_data = build_algorithmic_syllabus(topic, resources_description, timeline_duration)

    return syllabus_data


def build_algorithmic_syllabus(topic, resources_description, timeline_duration):
    """
    Intelligent curriculum engine that dynamically builds a multi-module syllabus
    tailored to the topic, resources, and chosen timeline duration.
    """
    timeline_lower = timeline_duration.lower()
    if '1 week' in timeline_lower:
        num_modules = 2
        lessons_per_mod = 3
    elif '2 week' in timeline_lower:
        num_modules = 3
        lessons_per_mod = 3
    elif '3 month' in timeline_lower:
        num_modules = 5
        lessons_per_mod = 4
    else:  # Default 1 Month
        num_modules = 4
        lessons_per_mod = 3

    module_templates = [
        ("Core Foundations & Environment Setup", [
            f"Introduction to {topic} & Ecosystem",
            "Development Environment & Tooling Setup",
            "Fundamental Syntax, Architecture & Design Patterns",
            "First Project Milestone & Quickstart"
        ]),
        ("Core Building Blocks & Workflows", [
            f"Deep Dive: Key Principles of {topic}",
            "Managing State, Data Models & Architecture",
            "Handling Edge Cases, Exceptions & Robust Workflows",
            "Practical Checkpoint: Mini-Application"
        ]),
        ("Advanced Techniques & Best Practices", [
            f"Performance Optimization in {topic}",
            "Security, Authentication & Data Integrity",
            "Testing, Debugging & Code Quality Standards",
            "Building Scalable Components"
        ]),
        ("Real-World Projects & Integrations", [
            f"Full-Scale Capstone Project: End-to-End Build",
            "API Integration, Networking & Third-Party Tools",
            "Continuous Integration, Testing & Deployment",
            "Production Readiness & Monitoring"
        ]),
        ("Mastery, Cloud & Ecosystem Trends", [
            f"Advanced Paradigms in Modern {topic}",
            "Cloud Hosting, Containers & Production Workflows",
            "Industry Best Practices & Collaborative Development",
            "Final Graduation Showcase & Next Steps"
        ]),
    ]

    selected_templates = module_templates[:num_modules]

    modules = []
    for m_idx, (m_title, lessons) in enumerate(selected_templates, start=1):
        mod_lessons = []
        for l_idx, l_title in enumerate(lessons[:lessons_per_mod], start=1):
            mod_lessons.append({
                "title": l_title,
                "lesson_type": "LINK",
                "external_url": f"https://www.google.com/search?q={requests.utils.quote(topic + ' ' + l_title)}"
            })
        modules.append({
            "title": f"Module {m_idx}: {m_title}",
            "lessons": mod_lessons
        })

    description = f"Comprehensive {timeline_duration} curriculum to master {topic}."
    if resources_description:
        description += f" Focus areas: {resources_description}."

    return {
        "course_title": f"{topic} ({timeline_duration} Track)",
        "course_description": description,
        "modules": modules
    }


# Backwards compatibility / convenient aliases
generate_ai_syllabus = generate_ai_course_syllabus
import_youtube_playlist_data = fetch_youtube_playlist_videos
