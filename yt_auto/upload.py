"""선택: YouTube Data API 업로드 (pip install google-api-python-client google-auth-oauthlib, client_secret.json 필요)"""
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def upload(video, thumb, meta, privacy="private"):
    cred = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"]).run_local_server(port=0)
    yt = build("youtube", "v3", credentials=cred)
    r = yt.videos().insert(part="snippet,status", body={
        "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"], "categoryId": "22"},
        "status": {"privacyStatus": privacy}}, media_body=MediaFileUpload(video, resumable=True)).execute()
    yt.thumbnails().set(videoId=r["id"], media_body=MediaFileUpload(thumb)).execute()
    return r["id"]
