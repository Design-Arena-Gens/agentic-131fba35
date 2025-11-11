import urllib.request
import re

video_id = 'dQw4w9WgXcQ'
video_url = f'https://www.youtube.com/watch?v={video_id}'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

req = urllib.request.Request(video_url, headers=headers)

print(f"Fetching: {video_url}")
with urllib.request.urlopen(req, timeout=10) as response:
    html = response.read().decode('utf-8')

print(f"HTML Length: {len(html)}")

# Try multiple patterns to find continuation token
patterns = [
    (r'"continuationCommand":\s*{\s*"token":\s*"([^"]+)"', "Pattern 1: continuationCommand"),
    (r'"itemSectionContinuation":\s*{\s*"continuations":\s*\[\s*{\s*"nextContinuationData":\s*{\s*"continuation":\s*"([^"]+)"', "Pattern 2: itemSectionContinuation"),
    (r'"continuation":\s*"([^"]+)"', "Pattern 3: simple continuation")
]

for pattern, name in patterns:
    matches = re.findall(pattern, html)
    if matches:
        print(f"\n{name}: Found {len(matches)} matches")
        print(f"First token: {matches[0][:50]}...")
        break
else:
    print("\nNo continuation tokens found")

# Check if comments section exists
if 'commentsSection' in html:
    print("\nFound 'commentsSection' in HTML")
if 'itemSectionRenderer' in html:
    print("Found 'itemSectionRenderer' in HTML")
if 'commentThreadRenderer' in html:
    print("Found 'commentThreadRenderer' in HTML")
