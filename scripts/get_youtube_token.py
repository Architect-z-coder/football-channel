"""Run ONCE on your own computer to let the pipeline upload to your channel.

1. In Google Cloud Console: create a project, enable "YouTube Data API v3",
   create an OAuth client of type "Desktop app", download it as client_secret.json
   into this folder.
2. Set the OAuth consent screen to "In production" (otherwise the token expires after 7 days).
3. pip install google-auth-oauthlib
4. python scripts/get_youtube_token.py
5. Sign in with the Google account that owns the channel. Copy the three values it prints
   into your GitHub repository secrets.
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]

secret_file = Path(__file__).parent / "client_secret.json"
flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
client = json.loads(secret_file.read_text())["installed"]

print("\nAdd these as GitHub secrets:\n")
print("YT_CLIENT_ID     =", client["client_id"])
print("YT_CLIENT_SECRET =", client["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
print("\nKeep them private. Delete client_secret.json from this folder afterwards.")
