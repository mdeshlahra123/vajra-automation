"""One-time YouTube login on the laptop. Opens the browser, you approve, it writes yt-token.json
(refresh token, gitignored). The refresh token then goes into the GitHub secret YT_TOKEN.
Run: python social/yt_auth.py"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCOPES = ["https://www.googleapis.com/auth/youtube", "https://www.googleapis.com/auth/youtube.force-ssl", "https://www.googleapis.com/auth/youtube.upload"]
flow = InstalledAppFlow.from_client_secrets_file(os.path.join(ROOT, "yt-client.json"), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline",
                              authorization_prompt_message="Browser khul raha hai: mdeshlahra123@gmail.com se login karke Allow dabaiye.")
open(os.path.join(ROOT, "yt-token.json"), "w").write(creds.to_json())
print("saved yt-token.json, refresh token:", "yes" if creds.refresh_token else "NO")
