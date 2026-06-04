import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from requests.auth import HTTPBasicAuth

try:
    import requests
except ImportError as exc:
    raise ImportError(
        "The requests package is required for reddit_parser.py. Install it with `pip install requests`."
    ) from exc

from parsers.task import ParserRunTask

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _clean_token(value: Optional[str]) -> Optional[str]:
    if not value or value.strip() in {"", "your_reddit_bearer_token_here"}:
        return None
    return value.strip()


class RedditParser:
    source_type = "reddit"

    def __init__(
        self,
        bearer_token: Optional[str] = None,
        endpoint: str = "https://oauth.reddit.com",
        user_agent: Optional[str] = None,
    ):
        self.bearer_token = _clean_token(bearer_token or os.environ.get("REDDIT_BEARER_TOKEN"))
        if self.bearer_token is None and load_dotenv is not None:
            env_path = Path(".env")
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                self.bearer_token = _clean_token(os.environ.get("REDDIT_BEARER_TOKEN"))

        if not self.bearer_token:
            self.bearer_token = self._request_bearer_token()

        self.endpoint = os.environ.get("REDDIT_ENDPOINT", endpoint)
        self.user_agent = user_agent or os.environ.get(
            "REDDIT_USER_AGENT", "reddit-models-parser/1.0"
        )

        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": self.user_agent,
            }
        )

    def run(self, task: ParserRunTask) -> list[dict[str, Any]]:
        filters = task.filters or {}
        subreddit = filters.get("subreddit")
        query = filters.get("query")
        sort = filters.get("sort", "hot")
        max_items = task.max_items or 100

        if subreddit:
            path = f"/r/{subreddit}/{sort}.json"
            params = {"limit": min(max_items, 100)}
        elif query:
            path = "/search.json"
            params = {
                "q": query,
                "limit": min(max_items, 100),
                "sort": filters.get("sort", "relevance"),
                "restrict_sr": int(bool(filters.get("restrict_sr", False))),
                "t": filters.get("time_filter", "all"),
            }
        else:
            raise ValueError(
                "RedditParser requires either filters['subreddit'] or filters['query']."
            )

        raw_items: list[dict[str, Any]] = []
        seen = set()
        after = None
        fetched = 0

        while True:
            if after:
                params["after"] = after

            response = self.session.get(
                f"{self.endpoint}{path}", params=params, timeout=30
            )
            response.raise_for_status()
            data = response.json().get("data", {})
            children = data.get("children", [])

            if not children:
                break

            for entry in children:
                post = entry.get("data", {})
                item = self._map_post_to_raw_item(post, task)
                external_id = item.get("external_id")
                if external_id and external_id in seen:
                    continue
                if external_id:
                    seen.add(external_id)

                if not self._pass_local_filters(item, task):
                    item["status"] = "skipped"
                else:
                    item["status"] = "raw"

                raw_items.append(item)
                fetched += 1

                if getattr(task, "delay_between_items", None):
                    time.sleep(task.delay_between_items)

                if task.max_items and fetched >= task.max_items:
                    break

            if task.max_items and fetched >= task.max_items:
                break

            after = data.get("after")
            if not after:
                break

            if getattr(task, "delay_seconds", 0):
                time.sleep(task.delay_seconds)

            remaining = (task.max_items or 0) - fetched
            params["limit"] = min(remaining if remaining > 0 else 100, 100)

        return raw_items

    def _map_post_to_raw_item(self, post: dict[str, Any], task: ParserRunTask) -> dict[str, Any]:
        created_at = self._parse_timestamp(post.get("created_utc"))

        return {
            "source_id": None,
            "external_id": f"reddit_{post.get('id')}" if post.get("id") else None,
            "title": post.get("title") or post.get("selftext") or None,
            "model_type": None,
            "domain": ["Reddit"],
            "description": post.get("selftext") or None,
            "url": f"https://reddit.com{post.get('permalink')}" if post.get("permalink") else None,
            "author": post.get("author"),
            "license": None,
            "tags": self._extract_tags(post),
            "likes": post.get("score"),
            "num_comments": post.get("num_comments"),
            "downloads": None,
            "downloads_all_time": None,
            "citations": None,
            "created_at_source": created_at,
            "updated_at_source": created_at,
            "language": [],
            "framework": [],
            "task_type": [post.get("post_hint")] if post.get("post_hint") else [],
            "sha": None,
            "raw_json": post,
            "collected_at": datetime.now(timezone.utc),
            "task_id": str(task.task_id),
            "status": "raw",
        }

    def _pass_local_filters(self, item: dict[str, Any], task: ParserRunTask) -> bool:
        filters = task.filters or {}

        if task.date_from and item.get("created_at_source"):
            if item["created_at_source"] < task.date_from:
                return False

        if task.date_to and item.get("created_at_source"):
            if item["created_at_source"] >= task.date_to:
                return False

        min_score = filters.get("min_score")
        if min_score is not None and (item.get("likes") or 0) < min_score:
            return False

        min_comments = filters.get("min_comments")
        if min_comments is not None and (item.get("num_comments") or 0) < min_comments:
            return False

        return True

    @staticmethod
    def _parse_timestamp(value: Optional[float]) -> Optional[datetime]:
        if value is None:
            return None
        return datetime.fromtimestamp(value, timezone.utc)

    @staticmethod
    def _extract_tags(post: dict[str, Any]) -> list[str]:
        tags = []
        subreddit = post.get("subreddit")
        if subreddit:
            tags.append(f"subreddit:{subreddit}")
        flair = post.get("link_flair_text")
        if flair:
            tags.append(f"flair:{flair}")
        if post.get("over_18"):
            tags.append("nsfw")
        return tags

    @staticmethod
    def _request_bearer_token() -> str:
        client_id = os.environ.get("REDDIT_CLIENT_ID")
        client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
        user_agent = os.environ.get("REDDIT_USER_AGENT", "reddit-models-parser/1.0")
        if not client_id or not client_secret:
            raise ValueError(
                "Set REDDIT_BEARER_TOKEN or REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET for RedditParser."
            )

        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=HTTPBasicAuth(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": user_agent},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("Reddit token response did not include access_token.")
        return token
