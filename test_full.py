import urllib.request
import re
import json

video_id = 'dQw4w9WgXcQ'
video_url = f'https://www.youtube.com/watch?v={video_id}'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

req = urllib.request.Request(video_url, headers=headers)

print(f"Step 1: Fetching video page...")
with urllib.request.urlopen(req, timeout=10) as response:
    html = response.read().decode('utf-8')

print(f"HTML Length: {len(html)}")

# Find continuation token
match = re.search(r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', html)
if match:
    continuation_token = match.group(1)
    print(f"Found token: {continuation_token[:50]}...")
else:
    print("No token found")
    exit()

print("\nStep 2: Fetching comments with innertube API...")
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

with urllib.request.urlopen(req, timeout=10) as response:
    data = json.loads(response.read().decode('utf-8'))

print(f"API Response keys: {list(data.keys())}")

# Try to find comments
comments = []
actions = data.get('onResponseReceivedEndpoints', [])
print(f"Found {len(actions)} actions")

for i, action in enumerate(actions):
    print(f"\nAction {i}: {list(action.keys())}")

    if 'reloadContinuationItemsCommand' in action:
        items = action['reloadContinuationItemsCommand'].get('continuationItems', [])
        print(f"  reloadContinuationItemsCommand: {len(items)} items")
    elif 'appendContinuationItemsAction' in action:
        items = action['appendContinuationItemsAction'].get('continuationItems', [])
        print(f"  appendContinuationItemsAction: {len(items)} items")
    else:
        continue

    for j, item in enumerate(items[:3]):
        print(f"    Item {j}: {list(item.keys())}")
        if 'commentThreadRenderer' in item:
            thread = item['commentThreadRenderer']
            comment = thread.get('comment', {}).get('commentRenderer', {})
            author = comment.get('authorText', {}).get('simpleText', 'N/A')
            print(f"      Comment author: {author}")
            comments.append({'author': author})

print(f"\nTotal comments found: {len(comments)}")
