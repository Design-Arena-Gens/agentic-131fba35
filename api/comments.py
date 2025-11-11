"""
YouTube Comments API - Simple implementation using yt-dlp approach
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re
import json
import urllib.request
import urllib.error


def extract_video_id(url):
    """Extract video ID from YouTube URL or return as-is if already an ID"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If it looks like a video ID, return it
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None


def fetch_youtube_comments(video_id, max_results=50):
    """
    Fetch YouTube comments for a given video ID.
    Returns a simplified response format.
    """
    try:
        # Step 1: Fetch video page HTML to extract initial data
        video_url = f'https://www.youtube.com/watch?v={video_id}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }

        req = urllib.request.Request(video_url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                html = response.read().decode('utf-8')
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fetch video: {str(e)}',
                'video_id': video_id
            }

        # Step 2: Extract continuation token for comments section
        token_match = re.search(r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', html)

        if not token_match:
            return {
                'success': True,
                'video_id': video_id,
                'comments': [],
                'message': 'No comments found (may be disabled)'
            }

        continuation_token = token_match.group(1)

        # Step 3: Call YouTube innertube API to get comments
        api_url = 'https://www.youtube.com/youtubei/v1/next?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'
        payload = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20240101.00.00'
                }
            },
            'continuation': continuation_token
        }

        api_req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': headers['User-Agent']
            }
        )

        try:
            with urllib.request.urlopen(api_req, timeout=15) as response:
                api_data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to fetch comments API: {str(e)}',
                'video_id': video_id
            }

        # Step 4: Parse comments from API response
        # YouTube now uses entityBatchUpdate for comments data
        comments = []

        # Get mutations from frameworkUpdates
        framework_updates = api_data.get('frameworkUpdates', {})
        entity_batch_update = framework_updates.get('entityBatchUpdate', {})
        mutations = entity_batch_update.get('mutations', [])

        # Also track comment order from onResponseReceivedEndpoints
        comment_ids = []
        actions = api_data.get('onResponseReceivedEndpoints', [])
        for action in actions:
            items = []
            if 'reloadContinuationItemsCommand' in action:
                items = action['reloadContinuationItemsCommand'].get('continuationItems', [])
            elif 'appendContinuationItemsAction' in action:
                items = action['appendContinuationItemsAction'].get('continuationItems', [])

            for item in items:
                if 'commentThreadRenderer' in item:
                    thread = item['commentThreadRenderer']
                    view_model = thread.get('commentViewModel', {}).get('commentViewModel', {})
                    comment_id = view_model.get('commentId')
                    if comment_id:
                        comment_ids.append(comment_id)

        # Extract comment data from mutations
        comment_map = {}
        for mutation in mutations:
            payload = mutation.get('payload', {})
            if 'commentEntityPayload' not in payload:
                continue

            comment_payload = payload['commentEntityPayload']
            properties = comment_payload.get('properties', {})

            comment_id = properties.get('commentId')
            if not comment_id:
                continue

            # Extract text
            content_data = properties.get('content', {})
            text = content_data.get('content', '')

            # Extract author (from authorButtonA11y field)
            author = properties.get('authorButtonA11y', 'Unknown')

            # Extract published time
            published = properties.get('publishedTime', '')

            # Extract toolbar for likes
            toolbar = properties.get('toolbar', {})
            like_count = toolbar.get('likeCountLiked', toolbar.get('likeCountNotliked', '0'))

            comment_map[comment_id] = {
                'author': author,
                'text': text,
                'likes': like_count,
                'published': published
            }

        # Reconstruct comments in order
        for comment_id in comment_ids:
            if comment_id in comment_map:
                comments.append(comment_map[comment_id])
                if len(comments) >= max_results:
                    break

        return {
            'success': True,
            'video_id': video_id,
            'comments': comments,
            'count': len(comments)
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'video_id': video_id
        }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler"""

    def do_GET(self):
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)

        # Root endpoint - Serve HTML page
        if parsed_url.path == '/':
            try:
                with open('public/index.html', 'r') as f:
                    html_content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(html_content.encode())
                return
            except FileNotFoundError:
                pass

        # Set CORS headers for API responses
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        # Comments endpoint
        if parsed_url.path == '/comments':
            url_param = params.get('url', [None])[0]

            if not url_param:
                error = {
                    'success': False,
                    'error': 'Missing required parameter: url'
                }
                self.wfile.write(json.dumps(error).encode())
                return

            try:
                max_results = int(params.get('max', [50])[0])
                max_results = min(max_results, 100)  # Cap at 100
            except (ValueError, IndexError):
                max_results = 50

            video_id = extract_video_id(url_param)

            if not video_id:
                error = {
                    'success': False,
                    'error': 'Invalid YouTube URL or video ID'
                }
                self.wfile.write(json.dumps(error).encode())
                return

            # Fetch and return comments
            result = fetch_youtube_comments(video_id, max_results)
            self.wfile.write(json.dumps(result, indent=2).encode())
            return

        # 404 for unknown endpoints
        error = {'success': False, 'error': 'Not found'}
        self.wfile.write(json.dumps(error).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
