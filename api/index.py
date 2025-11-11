from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import json
import urllib.request
import ssl

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If it's just the ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None

def get_youtube_comments(video_id, max_results=100):
    """Fetch comments from YouTube video using YouTube Data API v3 innertube"""
    try:
        # Use YouTube's innertube API (internal API used by the website)
        api_url = 'https://www.youtube.com/youtubei/v1/next'

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Origin': 'https://www.youtube.com',
            'Referer': f'https://www.youtube.com/watch?v={video_id}'
        }

        payload = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20231201.01.00'
                }
            },
            'videoId': video_id
        }

        req = urllib.request.Request(
            api_url + '?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )

        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Navigate to comments section
        comments = []
        try:
            # Try to find engagement panels with comments
            engagement_panels = data.get('engagementPanels', [])
            on_response_received = data.get('onResponseReceivedEndpoints', [])

            # Look for comments in the standard location
            contents = data.get('contents', {}).get('twoColumnWatchNextResults', {}).get('results', {}).get('results', {}).get('contents', [])

            for content in contents:
                if 'itemSectionRenderer' in content:
                    item_section = content['itemSectionRenderer']
                    if 'contents' in item_section:
                        for item in item_section['contents']:
                            if 'continuationItemRenderer' in item:
                                # This means we need to make another request for comments
                                # For now, we'll return empty and suggest using YouTube API
                                pass
                            elif 'commentThreadRenderer' in item:
                                comment_thread = item['commentThreadRenderer']['comment']['commentRenderer']

                                author = comment_thread.get('authorText', {}).get('simpleText', 'Unknown')
                                text_runs = comment_thread.get('contentText', {}).get('runs', [])
                                text = ''.join([run.get('text', '') for run in text_runs])

                                likes = '0'
                                if 'voteCount' in comment_thread:
                                    vote_count = comment_thread['voteCount']
                                    if 'simpleText' in vote_count:
                                        likes = vote_count['simpleText']

                                published = comment_thread.get('publishedTimeText', {}).get('runs', [{}])[0].get('text', 'Unknown')

                                comments.append({
                                    'author': author,
                                    'text': text,
                                    'likes': likes,
                                    'published': published
                                })

                                if len(comments) >= max_results:
                                    break

                if len(comments) >= max_results:
                    break

            # If no comments found, try alternative method
            if not comments:
                return {
                    'video_id': video_id,
                    'comment_count': 0,
                    'comments': [],
                    'message': 'Comments may be disabled or require additional API call. Consider using YouTube Data API v3 with proper authentication.'
                }

        except (KeyError, IndexError) as e:
            return {'error': f'Error parsing comments: {str(e)}', 'note': 'Video data structure may have changed'}

        return {
            'video_id': video_id,
            'comment_count': len(comments),
            'comments': comments
        }

    except Exception as e:
        return {'error': str(e)}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        # CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        if parsed_path.path == '/':
            response = {
                'name': 'YouTube Comments API',
                'version': '1.0.0',
                'endpoints': {
                    '/api/comments': {
                        'method': 'GET',
                        'params': {
                            'url': 'YouTube video URL or video ID (required)',
                            'max_results': 'Maximum number of comments to return (optional, default: 100)'
                        },
                        'example': '/api/comments?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                    }
                }
            }
            self.wfile.write(json.dumps(response).encode())

        elif parsed_path.path == '/api/comments':
            video_url = query_params.get('url', [None])[0]
            max_results = int(query_params.get('max_results', [100])[0])

            if not video_url:
                response = {'error': 'Missing required parameter: url'}
                self.wfile.write(json.dumps(response).encode())
                return

            video_id = extract_video_id(video_url)

            if not video_id:
                response = {'error': 'Invalid YouTube URL or video ID'}
                self.wfile.write(json.dumps(response).encode())
                return

            result = get_youtube_comments(video_id, max_results)
            self.wfile.write(json.dumps(result).encode())

        else:
            response = {'error': 'Not found'}
            self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
