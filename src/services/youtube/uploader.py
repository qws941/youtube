from __future__ import annotations

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from googleapiclient.errors import HttpError, ResumableUploadError  # type: ignore[import-untyped]
from googleapiclient.http import MediaFileUpload  # type: ignore[import-untyped]

from src.core.exceptions import (
    YouTubeAPIError,
    YouTubeQuotaExceededError,
    YouTubeUploadError,
)
from src.core.interfaces import YouTubeUploader as YouTubeUploaderBase
from src.services.youtube.auth import YouTubeAuth

RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (IOError, ResumableUploadError)
MAX_RETRIES = 10
CHUNK_SIZE = 10 * 1024 * 1024

_executor = ThreadPoolExecutor(max_workers=2)


class YouTubeUploader(YouTubeUploaderBase):
    def __init__(self, auth: YouTubeAuth | None = None) -> None:
        self._auth = auth or YouTubeAuth()

    @property
    def youtube(self) -> Any:
        return self._auth.youtube

    @property
    def analytics(self) -> Any:
        return self._auth.analytics

    async def upload(
        self,
        video_path: str | Path,
        title: str,
        description: str,
        tags: list[str],
        thumbnail_path: str | Path | None = None,
        scheduled_at: str | None = None,
        category_id: str = "22",
        privacy_status: str = "private",
        made_for_kids: bool = False,
    ) -> str:
        video_path = Path(video_path)
        if not video_path.exists():
            raise YouTubeUploadError(f"Video file not found: {video_path}")

        body: dict[str, Any] = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:500] if tags else [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        if scheduled_at:
            body["status"]["privacyStatus"] = "private"
            body["status"]["publishAt"] = self._format_scheduled_time(scheduled_at)

        loop = asyncio.get_event_loop()
        video_id: str = await loop.run_in_executor(
            _executor, self._sync_upload, video_path, body
        )

        if thumbnail_path:
            await self.update_thumbnail(video_id, thumbnail_path)

        return video_id

    def _sync_upload(self, video_path: Path, body: dict[str, Any]) -> str:
        media = MediaFileUpload(
            str(video_path),
            chunksize=CHUNK_SIZE,
            resumable=True,
            mimetype="video/*",
        )

        try:
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )
            return self._resumable_upload(request)
        except HttpError as e:
            self._handle_http_error(e)
            raise YouTubeUploadError("Upload failed") from e

    def _resumable_upload(self, request: Any) -> str:
        response = None
        error: Exception | None = None
        retry = 0

        while response is None:
            try:
                _, response = request.next_chunk()
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = e
                else:
                    self._handle_http_error(e)
                    raise YouTubeUploadError("Upload failed") from e
            except RETRIABLE_EXCEPTIONS as e:
                error = e

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    raise YouTubeUploadError(f"Upload failed after {MAX_RETRIES} retries")

                sleep_seconds = random.random() * (2 ** retry)
                time.sleep(min(sleep_seconds, 300))
                error = None

        return str(response["id"])

    def _format_scheduled_time(self, scheduled_at: str) -> str:
        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    async def update_thumbnail(self, video_id: str, thumbnail_path: str | Path) -> bool:
        thumbnail_path = Path(thumbnail_path)
        if not thumbnail_path.exists():
            return False

        loop = asyncio.get_event_loop()
        result: bool = await loop.run_in_executor(
            _executor, self._sync_update_thumbnail, video_id, thumbnail_path
        )
        return result

    def _sync_update_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        try:
            suffix = thumbnail_path.suffix.lower()
            mimetype = "image/jpeg" if suffix in [".jpg", ".jpeg"] else "image/png"
            media = MediaFileUpload(str(thumbnail_path), mimetype=mimetype)
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media,
            ).execute()
            return True
        except HttpError as e:
            if e.resp.status == 403:
                return False
            self._handle_http_error(e)
            return False

    async def get_analytics(
        self,
        video_id: str,
        metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        if metrics is None:
            metrics = [
                "views", "likes", "comments", "shares",
                "estimatedMinutesWatched", "averageViewDuration",
            ]

        loop = asyncio.get_event_loop()
        result: dict[str, Any] = await loop.run_in_executor(
            _executor, self._sync_get_analytics, video_id, metrics
        )
        return result

    def _sync_get_analytics(self, video_id: str, metrics: list[str]) -> dict[str, Any]:
        try:
            channel_response = self.youtube.channels().list(
                part="id",
                mine=True,
            ).execute()

            if not channel_response.get("items"):
                return {"video_id": video_id, "error": "No channel found"}

            channel_id = channel_response["items"][0]["id"]
            end_date = datetime.now(UTC).strftime("%Y-%m-%d")
            start_date = "2020-01-01"

            response = self.analytics.reports().query(
                ids=f"channel=={channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics=",".join(metrics),
                filters=f"video=={video_id}",
            ).execute()

            result: dict[str, Any] = {"video_id": video_id}
            if response.get("rows") and response.get("columnHeaders"):
                headers = [h["name"] for h in response["columnHeaders"]]
                values = response["rows"][0]
                for header, value in zip(headers, values, strict=False):
                    result[header] = value

            return result
        except HttpError as e:
            if e.resp.status in [403, 404]:
                return {"video_id": video_id, "error": "Analytics unavailable"}
            self._handle_http_error(e)
            return {"video_id": video_id, "error": str(e)}

    async def get_video_details(self, video_id: str) -> dict[str, Any]:
        loop = asyncio.get_event_loop()
        result: dict[str, Any] = await loop.run_in_executor(
            _executor, self._sync_get_video_details, video_id
        )
        return result

    def _sync_get_video_details(self, video_id: str) -> dict[str, Any]:
        try:
            response = self.youtube.videos().list(
                part="snippet,statistics,status",
                id=video_id,
            ).execute()

            if not response.get("items"):
                return {}

            item = response["items"][0]
            return {
                "id": video_id,
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "published_at": item["snippet"]["publishedAt"],
                "channel_id": item["snippet"]["channelId"],
                "privacy_status": item["status"]["privacyStatus"],
                "view_count": int(item["statistics"].get("viewCount", 0)),
                "like_count": int(item["statistics"].get("likeCount", 0)),
                "comment_count": int(item["statistics"].get("commentCount", 0)),
            }
        except HttpError as e:
            self._handle_http_error(e)
            return {}

    async def update_video(
        self,
        video_id: str,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        category_id: str | None = None,
    ) -> bool:
        loop = asyncio.get_event_loop()
        result: bool = await loop.run_in_executor(
            _executor,
            self._sync_update_video,
            video_id,
            title,
            description,
            tags,
            category_id,
        )
        return result

    def _sync_update_video(
        self,
        video_id: str,
        title: str | None,
        description: str | None,
        tags: list[str] | None,
        category_id: str | None,
    ) -> bool:
        try:
            current = self.youtube.videos().list(
                part="snippet",
                id=video_id,
            ).execute()

            if not current.get("items"):
                return False

            snippet = current["items"][0]["snippet"]

            if title:
                snippet["title"] = title[:100]
            if description:
                snippet["description"] = description[:5000]
            if tags is not None:
                snippet["tags"] = tags[:500]
            if category_id:
                snippet["categoryId"] = category_id

            self.youtube.videos().update(
                part="snippet",
                body={"id": video_id, "snippet": snippet},
            ).execute()
            return True
        except HttpError as e:
            self._handle_http_error(e)
            return False

    async def delete_video(self, video_id: str) -> bool:
        loop = asyncio.get_event_loop()
        result: bool = await loop.run_in_executor(
            _executor, self._sync_delete_video, video_id
        )
        return result

    def _sync_delete_video(self, video_id: str) -> bool:
        try:
            self.youtube.videos().delete(id=video_id).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return False
            self._handle_http_error(e)
            return False

    def _handle_http_error(self, error: HttpError) -> None:
        status = error.resp.status
        reason = error._get_reason() if hasattr(error, "_get_reason") else str(error)

        if status == 403 and "quotaExceeded" in reason:
            raise YouTubeQuotaExceededError("YouTube API quota exceeded. Retry tomorrow.")

        if status == 403 and "forbidden" in reason.lower():
            raise YouTubeAPIError(f"Access forbidden: {reason}")

        if status == 401:
            raise YouTubeAPIError("Authentication failed. Re-authenticate required.")

        if status == 404:
            raise YouTubeAPIError(f"Resource not found: {reason}")

        raise YouTubeAPIError(f"YouTube API error ({status}): {reason}")
