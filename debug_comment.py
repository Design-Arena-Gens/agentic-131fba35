import urllib.request
import re
import json

video_id = 'dQw4w9WgXcQ'
video_url = f'https://www.youtube.com/watch?v={video_id}'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

req = urllib.request.Request(video_url, headers=headers)
with urllib.request.urlopen(req, timeout=15) as response:
    html = response.read().decode('utf-8')

token_match = re.search(r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', html)
continuation_token = token_match.group(1)

print(f"Continuation token: {continuation_token[:50]}...")

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

with urllib.request.urlopen(api_req, timeout=15) as response:
    api_data = json.loads(response.read().decode('utf-8'))

actions = api_data.get('onResponseReceivedEndpoints', [])
print(f"\nFound {len(actions)} actions")

for i, action in enumerate(actions):
    items = []
    if 'reloadContinuationItemsCommand' in action:
        items = action['reloadContinuationItemsCommand'].get('continuationItems', [])
    elif 'appendContinuationItemsAction' in action:
        items = action['appendContinuationItemsAction'].get('continuationItems', [])

    print(f"\nAction {i}: {len(items)} items")

    for j, item in enumerate(items[:2]):
        if 'commentThreadRenderer' in item:
            thread = item['commentThreadRenderer']
            comment_data = thread.get('comment', {}).get('commentRenderer', {})

            print(f"\n  Comment {j}:")
            print(f"    Keys: {list(comment_data.keys())}")

            # Try different ways to get author
            author_text = comment_data.get('authorText')
            print(f"    authorText type: {type(author_text)}")
            print(f"    authorText: {json.dumps(author_text, indent=6)[:200]}")

            # Try different ways to get content
            content = comment_data.get('contentText')
            print(f"    contentText type: {type(content)}")
            if content:
                print(f"    contentText keys: {list(content.keys()) if isinstance(content, dict) else 'not a dict'}")
                if 'runs' in content:
                    for k, run in enumerate(content['runs'][:1]):
                        print(f"      run {k}: {run.get('text', 'NO TEXT')[:100]}")
