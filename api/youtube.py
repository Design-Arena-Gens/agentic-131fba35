from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import json
import urllib.request
import urllib.error

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

    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None

def get_youtube_comments(video_id, max_results=100):
    """Fetch comments using youtube-comment-downloader approach"""
    try:
        # First, get the continuation token by fetching the video page
        video_url = f'https://www.youtube.com/watch?v={video_id}'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        req = urllib.request.Request(video_url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
        except urllib.error.URLError as e:
            return {'error': f'Failed to fetch video page: {str(e)}'}

        # Try multiple patterns to find continuation token
        continuation_token = None

        # Pattern 1: Direct continuation token
        match1 = re.search(r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', html)
        if match1:
            continuation_token = match1.group(1)

        # Pattern 2: itemSectionContinuation
        if not continuation_token:
            match2 = re.search(r'"itemSectionContinuation":\s*{\s*"continuations":\s*\[\s*{\s*"nextContinuationData":\s*{\s*"continuation":\s*"([^"]+)"', html)
            if match2:
                continuation_token = match2.group(1)

        # Pattern 3: Simple continuation field
        if not continuation_token:
            match3 = re.search(r'"continuation":\s*"([^"]+)"', html)
            if match3:
                continuation_token = match3.group(1)

        if not continuation_token:
            return {
                'video_id': video_id,
                'comment_count': 0,
                'comments': [],
                'message': 'Comments may be disabled or unavailable for this video',
                'debug': 'No continuation token found'
            }

        # Now fetch comments using the innertube API
        api_url = 'https://www.youtube.com/youtubei/v1/next?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'

        payload = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20231201.01.00'
                }
            },
            'continuation': continuation_token
        }

        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': headers['User-Agent']
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {'error': f'Failed to fetch comments: {str(e)}'}

        # Parse comments
        comments = []

        try:
            actions = data.get('onResponseReceivedEndpoints', [])

            for action in actions:
                if 'reloadContinuationItemsCommand' in action:
                    items = action['reloadContinuationItemsCommand'].get('continuationItems', [])
                elif 'appendContinuationItemsAction' in action:
                    items = action['appendContinuationItemsAction'].get('continuationItems', [])
                else:
                    continue

                for item in items:
                    if 'commentThreadRenderer' not in item:
                        continue

                    thread = item['commentThreadRenderer']
                    comment_renderer = thread.get('comment', {}).get('commentRenderer', {})

                    if not comment_renderer:
                        continue

                    # Extract author
                    author = comment_renderer.get('authorText', {}).get('simpleText', 'Unknown')

                    # Extract comment text
                    content_text = comment_renderer.get('contentText', {})
                    if 'runs' in content_text:
                        text = ''.join([run.get('text', '') for run in content_text['runs']])
                    elif 'simpleText' in content_text:
                        text = content_text['simpleText']
                    else:
                        text = ''

                    # Extract likes
                    likes = '0'
                    vote_count = comment_renderer.get('voteCount', {})
                    if 'simpleText' in vote_count:
                        likes = vote_count['simpleText']
                    elif 'accessibility' in vote_count:
                        likes_text = vote_count.get('accessibility', {}).get('accessibilityData', {}).get('label', '0')
                        likes = re.search(r'\d+', likes_text)
                        likes = likes.group(0) if likes else '0'

                    # Extract publish time
                    published_time = comment_renderer.get('publishedTimeText', {})
                    if 'runs' in published_time:
                        published = published_time['runs'][0].get('text', 'Unknown')
                    elif 'simpleText' in published_time:
                        published = published_time['simpleText']
                    else:
                        published = 'Unknown'

                    # Extract author thumbnail
                    author_thumbnail = ''
                    thumbnails = comment_renderer.get('authorThumbnail', {}).get('thumbnails', [])
                    if thumbnails:
                        author_thumbnail = thumbnails[0].get('url', '')

                    comments.append({
                        'author': author,
                        'text': text,
                        'likes': likes,
                        'published': published,
                        'author_thumbnail': author_thumbnail
                    })

                    if len(comments) >= max_results:
                        break

                if len(comments) >= max_results:
                    break

        except Exception as e:
            return {'error': f'Error parsing comments: {str(e)}'}

        return {
            'video_id': video_id,
            'comment_count': len(comments),
            'comments': comments
        }

    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}'}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        if parsed_path.path == '/' or parsed_path.path == '/api/youtube':
            response = {
                'name': 'YouTube Comments API',
                'version': '1.0.0',
                'endpoints': {
                    '/api/youtube/comments': {
                        'method': 'GET',
                        'params': {
                            'url': 'YouTube video URL or video ID (required)',
                            'max_results': 'Maximum number of comments (optional, default: 100)'
                        },
                        'example': '/api/youtube/comments?url=https://www.youtube.com/watch?v=jNQXAC9IVRw'
                    }
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif parsed_path.path == '/api/youtube/comments':
            video_url = query_params.get('url', [None])[0]

            if not video_url:
                response = {'error': 'Missing required parameter: url'}
                self.wfile.write(json.dumps(response).encode())
                return

            try:
                max_results = int(query_params.get('max_results', [100])[0])
            except ValueError:
                max_results = 100

            video_id = extract_video_id(video_url)

            if not video_id:
                response = {'error': 'Invalid YouTube URL or video ID'}
                self.wfile.write(json.dumps(response).encode())
                return

            result = get_youtube_comments(video_id, max_results)
            self.wfile.write(json.dumps(result, indent=2).encode())

        else:
            response = {'error': 'Not found'}
            self.wfile.write(json.dumps(response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
