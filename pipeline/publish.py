"""Publisher: uploads the video as PRIVATE, with captions and a thumbnail. You publish it after review."""
from pathlib import Path

from .common import log, secret

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def _youtube():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=secret("YT_REFRESH_TOKEN", required=True),
        client_id=secret("YT_CLIENT_ID", required=True),
        client_secret=secret("YT_CLIENT_SECRET", required=True),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(cfg: dict, script: dict, video: Path, srt: Path, thumbs: list[Path]) -> str:
    from googleapiclient.http import MediaFileUpload

    yt = _youtube()
    body = {
        "snippet": {
            "title": script["title_options"][0][:100],
            "description": script["description"],
            "tags": script.get("tags", [])[:15],
            "categoryId": cfg["youtube"]["category_id"],
            "defaultLanguage": cfg["channel"]["language"],
            "defaultAudioLanguage": cfg["channel"]["language"],
        },
        "status": {
            "privacyStatus": "private",  # never public automatically
            "selfDeclaredMadeForKids": cfg["youtube"]["made_for_kids"],
        },
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024,
                                                        resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    log.info("Uploaded as private: %s", vid)

    try:
        yt.captions().insert(part="snippet", body={"snippet": {
            "videoId": vid, "language": cfg["channel"]["language"], "name": "English"}},
            media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
    except Exception as e:  # captions are nice to have; never block the upload
        log.warning("Caption upload failed: %s", e)
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbs[0]))).execute()
    except Exception as e:  # needs a phone-verified channel
        log.warning("Thumbnail upload failed (verify your channel by phone): %s", e)
    return vid


def upload_short(cfg: dict, short: dict, video: Path, main_video_id: str | None) -> str:
    """Upload one vertical short as PRIVATE, linking to the full video."""
    from googleapiclient.http import MediaFileUpload

    yt = _youtube()
    link = f"\n\nFull breakdown: https://youtu.be/{main_video_id}" if main_video_id else ""
    body = {
        "snippet": {
            "title": f"{short['title'][:88]} #shorts",
            "description": short["narration"] + link + "\n\n#football #shorts",
            "tags": ["football", "shorts", "football analysis"],
            "categoryId": cfg["youtube"]["category_id"],
            "defaultLanguage": cfg["channel"]["language"],
            "defaultAudioLanguage": cfg["channel"]["language"],
        },
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": cfg["youtube"]["made_for_kids"]},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    log.info("Short uploaded as private: %s", resp["id"])
    return resp["id"]
