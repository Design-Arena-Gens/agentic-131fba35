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

with urllib.request.urlopen(req, timeout=10) as response:
    html = response.read().decode('utf-8')

match = re.search(r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', html)
continuation_token = match.group(1)

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

# Look at first comment in detail
actions = data.get('onResponseReceivedEndpoints', [])
for action in actions:
    if 'reloadContinuationItemsCommand' in action:
        items = action['reloadContinuationItemsCommand'].get('continuationItems', [])
        for item in items:
            if 'commentThreadRenderer' in item:
                thread = item['commentThreadRenderer']
                comment = thread.get('comment', {}).get('commentRenderer', {})

                print("Comment keys:", list(comment.keys()))
                print("\nauthorText:", json.dumps(comment.get('authorText'), indent=2))
                print("\ncontentText:", json.dumps(comment.get('contentText'), indent=2))

                # Try to extract text
                content = comment.get('contentText', {})
                if 'runs' in content:
                    text = ''.join([run.get('text', '') for run in content['runs']])
                    print(f"\nExtracted text: {text[:200]}")

                break
        break
