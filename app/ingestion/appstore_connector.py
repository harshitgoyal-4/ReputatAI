"""Apple App Store customer review connector."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from app.ingestion.base_connector import ConnectorResult, FeedbackConnector
from app.ingestion.normalizer import NormalizedFeedback


class AppStoreConnector(FeedbackConnector):
    """Fetch live customer reviews for any iOS app from the Apple App Store."""

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    def __init__(self, app_id_or_name: str, country: str = "us", limit: int = 50) -> None:
        self.target = app_id_or_name.strip()
        self.country = country.strip().lower() or "us"
        self.limit = min(max(1, limit), 100)

    def _resolve_app_id(self) -> tuple[str, str, str | None]:
        """Resolve numeric app_id directly or lookup by app name. Returns (app_id, app_name, error)."""
        if self.target.isdigit():
            return self.target, f"App #{self.target}", None

        for country in [self.country, "us"]:
            search_url = f"https://itunes.apple.com/search?term={quote_plus(self.target)}&entity=software&limit=3&country={country}"
            req = Request(search_url, headers={"User-Agent": self.USER_AGENT})
            try:
                with urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    app_id = str(results[0].get("trackId", ""))
                    app_name = str(results[0].get("trackName", self.target))
                    if app_id:
                        return app_id, app_name, None
            except Exception:
                continue

        return "", "", f"No iOS app found on App Store matching '{self.target}'."

    def fetch(self) -> ConnectorResult:
        if not self.target:
            return ConnectorResult([], ["App ID or App Name cannot be empty."])

        app_id, app_name, err = self._resolve_app_id()
        if err or not app_id:
            return ConnectorResult([], [err or "Could not resolve App ID."])

        # Try multiple official RSS feed URL variations
        candidate_urls = [
            f"https://itunes.apple.com/{self.country}/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json",
            f"https://itunes.apple.com/{self.country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json",
            f"https://itunes.apple.com/{self.country}/rss/customerreviews/id={app_id}/json",
            f"https://itunes.apple.com/us/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json",
        ]

        payload = None
        last_error = None
        for url in candidate_urls:
            req = Request(url, headers={"User-Agent": self.USER_AGENT, "Accept": "application/json"})
            try:
                with urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    entries = data.get("feed", {}).get("entry")
                    if entries:
                        payload = data
                        break
            except Exception as exc:
                last_error = exc
                continue

        if not payload:
            return ConnectorResult(
                [],
                [
                    f"No customer reviews found for '{app_name}' (ID: {app_id}) in country '{self.country.upper()}'.",
                    "Tip: Popular apps often have more recent reviews in the 'US' or 'GB' store regions.",
                ],
            )

        raw_entries = payload.get("feed", {}).get("entry", [])
        if isinstance(raw_entries, dict):
            entries_list = [raw_entries]
        elif isinstance(raw_entries, list):
            entries_list = raw_entries
        else:
            entries_list = []

        records: list[NormalizedFeedback] = []
        for item in entries_list:
            if not isinstance(item, dict):
                continue

            # Only process entries that contain an actual review rating
            rating_obj = item.get("im:rating")
            if not rating_obj:
                continue

            try:
                review_id = str(item.get("id", {}).get("label", ""))
                title = str(item.get("title", {}).get("label", "")).strip()
                content = str(item.get("content", {}).get("label", "")).strip()
                rating_str = str(rating_obj.get("label", "3"))
                author = str(item.get("author", {}).get("name", {}).get("label", "App Store User"))
                updated = str(item.get("updated", {}).get("label", ""))[:10]
                link = str(item.get("link", {}).get("attributes", {}).get("href", ""))

                full_text = f"{title}: {content}" if title and content else title or content
                if not full_text:
                    continue

                records.append(
                    NormalizedFeedback(
                        id=f"appstore_{review_id or len(records)+1}",
                        date=updated or "2026-01-01",
                        platform=f"App Store ({app_name})",
                        author=author,
                        text=full_text,
                        rating=int(rating_str) if rating_str.isdigit() else 3,
                        source_url=link or None,
                        metadata={"app_id": app_id, "app_name": app_name, "country": self.country},
                    )
                )
                if len(records) >= self.limit:
                    break
            except Exception:
                continue

        if not records:
            return ConnectorResult([], [f"Could not parse reviews for '{app_name}' (ID: {app_id})."])

        return ConnectorResult(records, [])
