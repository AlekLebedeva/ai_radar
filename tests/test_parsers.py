import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from parsers.adapters import ArxivAdapter, HuggingFaceAdapter, RedditAdapter
from parsers.arxiv_parser import parse_arxiv_entry
from parsers.base import BaseParser
from parsers.pending import PendingParserAdapter
from parsers.parse import HuggingFaceModelsParser, _clean_token as clean_hf_token
from parsers.registry import PARSER_REGISTRY, get_parser_spec, get_source_payloads
from parsers.reddit_parser import RedditParser, _clean_token as clean_reddit_token
from parsers.task import ParserRunTask


TASK_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def make_task(**overrides):
    values = {
        "task_id": TASK_ID,
        "parser_name": "test",
        "date_from": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "date_to": datetime(2024, 2, 1, tzinfo=timezone.utc),
        "source_type": "test",
        "filters": {},
        "max_items": 100,
    }
    values.update(overrides)
    return ParserRunTask(**values)


class ConcreteParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
        return []

    def normalize(self, raw_item):
        return dict(raw_item)


class FakeHfApi:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list_models(self, **kwargs):
        self.calls.append(kwargs)
        filter_value = kwargs.get("filter") or []
        if "text-generation" in filter_value:
            return iter(self.pages.get("text-generation", []))
        if "image-classification" in filter_value:
            return iter(self.pages.get("image-classification", []))
        return iter(self.pages.get("default", []))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeRedditSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.headers = {}
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": dict(params), "timeout": timeout})
        return FakeResponse(self.payloads.pop(0))


class BaseParserTests(unittest.IsolatedAsyncioTestCase):
    async def test_base_parser_defaults_and_contract(self):
        parser = ConcreteParser("code", "Name", "https://example.test")

        self.assertEqual(parser.session_headers["Accept"], "application/json")
        self.assertEqual(parser.get_rate_limit(), {"requests_per_min": 30, "requests_per_hour": 500})
        self.assertEqual(parser.get_sleep_seconds(), 2.0)
        self.assertEqual(await parser.fetch(None, None), [])
        self.assertEqual(parser.normalize({"id": 1}), {"id": 1})


class HuggingFaceParserTests(unittest.TestCase):
    def test_clean_token_rejects_empty_and_placeholder_values(self):
        self.assertIsNone(clean_hf_token(None))
        self.assertIsNone(clean_hf_token("  "))
        self.assertIsNone(clean_hf_token("your_huggingface_token_here"))
        self.assertEqual(clean_hf_token(" abc "), "abc")

    def test_maps_model_to_raw_item_with_metadata(self):
        parser = HuggingFaceModelsParser(token="token")
        model = SimpleNamespace(
            id="org/model-name",
            tags=["transformers", "license:apache-2.0", "language:en", "task:summarization", "llm"],
            card_data={"description": "Useful model", "language": ["fr"]},
            created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            last_modified=datetime(2024, 1, 15, tzinfo=timezone.utc),
            pipeline_tag="text-generation",
            library_name="pytorch",
            likes=12,
            downloads=34,
            downloads_all_time=56,
            sha="abc123",
        )

        item = parser._map_model_to_raw_item(model, make_task())

        self.assertEqual(item["external_id"], "org/model-name")
        self.assertEqual(item["title"], "model-name")
        self.assertEqual(item["author"], "org")
        self.assertEqual(item["license"], "apache-2.0")
        self.assertEqual(item["model_type"], "transformer")
        self.assertEqual(item["domain"], ["LLM", "NLP"])
        self.assertEqual(item["language"], ["en", "fr"])
        self.assertEqual(item["framework"], ["pytorch", "transformers"])
        self.assertEqual(item["task_type"], ["summarization", "text-generation"])
        self.assertEqual(item["url"], "https://huggingface.co/org/model-name")
        self.assertEqual(item["task_id"], str(TASK_ID))
        self.assertEqual(item["status"], "raw")

    def test_run_applies_filters_deduplicates_and_marks_skipped(self):
        parser = HuggingFaceModelsParser(token="token")
        parser.api = FakeHfApi(
            {
                "default": [
                    SimpleNamespace(
                        id="org/first",
                        tags=["diffusers"],
                        card_data={},
                        last_modified=datetime(2024, 1, 10, tzinfo=timezone.utc),
                        pipeline_tag="text-to-image",
                        likes=10,
                        downloads=100,
                    ),
                    SimpleNamespace(
                        id="org/first",
                        tags=["diffusers"],
                        card_data={},
                        last_modified=datetime(2024, 1, 10, tzinfo=timezone.utc),
                        pipeline_tag="text-to-image",
                        likes=10,
                        downloads=100,
                    ),
                    SimpleNamespace(
                        id="org/low-downloads",
                        tags=[],
                        card_data={},
                        last_modified=datetime(2024, 1, 11, tzinfo=timezone.utc),
                        likes=1,
                        downloads=2,
                    ),
                ]
            }
        )
        task = make_task(
            filters={"tags": ["gguf"], "pipeline_tag": "text-to-image", "sort": "last_modified", "min_downloads": 50},
            max_items=10,
        )

        items = parser.run(task)

        self.assertEqual([item["external_id"] for item in items], ["org/first", "org/low-downloads"])
        self.assertEqual(items[0]["status"], "raw")
        self.assertEqual(items[1]["status"], "skipped")
        self.assertEqual(parser.api.calls[0]["filter"], ["gguf", "text-to-image"])
        self.assertEqual(parser.api.calls[0]["sort"], "lastModified")

    def test_run_parse_all_categories_uses_pipeline_tags_and_respects_max_items(self):
        parser = HuggingFaceModelsParser(token="token")
        parser.api = FakeHfApi(
            {
                "text-generation": [SimpleNamespace(id="org/text", tags=[], card_data={})],
                "image-classification": [SimpleNamespace(id="org/image", tags=[], card_data={})],
            }
        )
        task = make_task(
            filters={"pipeline_tags": ["text-generation", "image-classification"]},
            max_items=1,
            parse_all_categories=True,
        )

        items = parser.run(task)

        self.assertEqual([item["external_id"] for item in items], ["org/text"])
        self.assertEqual(len(parser.api.calls), 1)


class RedditParserTests(unittest.TestCase):
    def test_clean_token_rejects_empty_and_placeholder_values(self):
        self.assertIsNone(clean_reddit_token(None))
        self.assertIsNone(clean_reddit_token("  "))
        self.assertIsNone(clean_reddit_token("your_reddit_bearer_token_here"))
        self.assertEqual(clean_reddit_token(" abc "), "abc")

    def test_maps_post_to_raw_item(self):
        parser = RedditParser(bearer_token="token", endpoint="https://reddit.test")
        post = {
            "id": "abc",
            "title": "A post",
            "selftext": "Body",
            "permalink": "/r/MachineLearning/comments/abc/a_post/",
            "author": "user",
            "score": 42,
            "num_comments": 7,
            "created_utc": 1704067200,
            "subreddit": "MachineLearning",
            "link_flair_text": "Research",
            "over_18": True,
            "post_hint": "link",
        }

        item = parser._map_post_to_raw_item(post, make_task())

        self.assertEqual(item["external_id"], "reddit_abc")
        self.assertEqual(item["title"], "A post")
        self.assertEqual(item["description"], "Body")
        self.assertEqual(item["url"], "https://reddit.com/r/MachineLearning/comments/abc/a_post/")
        self.assertEqual(item["likes"], 42)
        self.assertEqual(item["num_comments"], 7)
        self.assertEqual(item["tags"], ["subreddit:MachineLearning", "flair:Research", "nsfw"])
        self.assertEqual(item["task_type"], ["link"])
        self.assertEqual(item["created_at_source"], datetime(2024, 1, 1, tzinfo=timezone.utc))

    def test_run_supports_search_pagination_deduplication_and_local_filters(self):
        parser = RedditParser(bearer_token="token", endpoint="https://reddit.test")
        parser.session = FakeRedditSession(
            [
                {
                    "data": {
                        "after": "page2",
                        "children": [
                            {"data": {"id": "one", "title": "One", "created_utc": 1704067200, "score": 10, "num_comments": 5}},
                            {"data": {"id": "one", "title": "One duplicate", "created_utc": 1704067200, "score": 10, "num_comments": 5}},
                        ],
                    }
                },
                {
                    "data": {
                        "after": None,
                        "children": [
                            {"data": {"id": "two", "title": "Two", "created_utc": 1704153600, "score": 1, "num_comments": 0}},
                        ],
                    }
                },
            ]
        )
        task = make_task(filters={"query": "models", "min_score": 5, "sort": "new"}, max_items=3)

        items = parser.run(task)

        self.assertEqual([item["external_id"] for item in items], ["reddit_one", "reddit_two"])
        self.assertEqual(items[0]["status"], "raw")
        self.assertEqual(items[1]["status"], "skipped")
        self.assertEqual(parser.session.calls[0]["url"], "https://reddit.test/search.json")
        self.assertEqual(parser.session.calls[0]["params"]["q"], "models")
        self.assertEqual(parser.session.calls[1]["params"]["after"], "page2")

    def test_run_requires_subreddit_or_query(self):
        parser = RedditParser(bearer_token="token")

        with self.assertRaisesRegex(ValueError, "subreddit.*query"):
            parser.run(make_task(filters={}))


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_huggingface_adapter_builds_task_and_normalizes_defaults(self):
        captured = {}

        class FakeParser:
            def run(self, task):
                captured["task"] = task
                return [{"external_id": "hf"}]

        with patch("parsers.adapters.HuggingFaceModelsParser", return_value=FakeParser()):
            adapter = HuggingFaceAdapter()
            result = await adapter.fetch(
                datetime(2024, 1, 1),
                datetime(2024, 1, 2, tzinfo=timezone.utc),
                filters={"parse_all_categories": True, "delay_seconds": "0.1", "delay_between_items": "0.2"},
                max_items=5,
                task_id=TASK_ID,
            )

        self.assertEqual(result, [{"external_id": "hf"}])
        self.assertEqual(captured["task"].parser_name, "huggingface")
        self.assertEqual(captured["task"].date_from.tzinfo, timezone.utc)
        self.assertTrue(captured["task"].parse_all_categories)
        self.assertEqual(captured["task"].delay_seconds, 0.1)
        normalized = adapter.normalize(
            {
                "likes": 3,
                "created_at_source": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "updated_at_source": datetime(2024, 1, 2, tzinfo=timezone.utc),
            }
        )
        self.assertEqual(normalized["popularity_metric"], 3)
        self.assertIsNone(normalized["created_at_source"].tzinfo)
        self.assertEqual(normalized["domain"], [])
        self.assertEqual(normalized["tags"], [])

    async def test_reddit_adapter_builds_task_and_normalizes_defaults(self):
        captured = {}

        class FakeParser:
            def run(self, task):
                captured["task"] = task
                return [{"external_id": "reddit"}]

        with patch("parsers.adapters.RedditParser", return_value=FakeParser()):
            adapter = RedditAdapter()
            result = await adapter.fetch(
                datetime(2024, 1, 1),
                datetime(2024, 1, 2, tzinfo=timezone.utc),
                filters={"subreddit": "MachineLearning"},
                max_items=5,
                task_id=TASK_ID,
            )

        self.assertEqual(result, [{"external_id": "reddit"}])
        self.assertEqual(captured["task"].parser_name, "reddit")
        self.assertEqual(captured["task"].source_type, "reddit")
        self.assertEqual(captured["task"].date_from.tzinfo, timezone.utc)
        normalized = adapter.normalize(
            {
                "likes": 8,
                "created_at_source": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "updated_at_source": datetime(2024, 1, 2, tzinfo=timezone.utc),
            }
        )
        self.assertEqual(normalized["popularity_metric"], 8)
        self.assertIsNone(normalized["updated_at_source"].tzinfo)
        self.assertEqual(normalized["domain"], ["Reddit"])
        self.assertEqual(normalized["framework"], [])

    async def test_arxiv_adapter_fetches_through_shared_parser_and_normalizes(self):
        captured = {}

        def fake_fetch(**kwargs):
            captured.update(kwargs)
            return [{"external_id": "2401.12345"}]

        with patch("parsers.adapters.fetch_arxiv_papers", side_effect=fake_fetch):
            adapter = ArxivAdapter()
            result = await adapter.fetch(
                datetime(2024, 1, 1),
                datetime(2024, 1, 2, tzinfo=timezone.utc),
                filters={"categories": "cs.AI", "delay_seconds": 0},
                max_items=5,
                task_id=TASK_ID,
            )

        self.assertEqual(result, [{"external_id": "2401.12345"}])
        self.assertEqual(captured["categories"], ["cs.AI"])
        self.assertEqual(captured["max_total"], 5)
        normalized = adapter.normalize({"citations": 4, "domain": None, "author": ["One", "Two"]})
        self.assertEqual(normalized["popularity_metric"], 4)
        self.assertEqual(normalized["domain"], [])
        self.assertEqual(normalized["author"], "One, Two")

    async def test_arxiv_entry_mapping(self):
        item = parse_arxiv_entry(
            {
                "id": "https://arxiv.org/abs/2401.12345v2",
                "title": " Test paper ",
                "summary": " Abstract ",
                "authors": [{"name": "Author"}],
                "categories": [{"term": "cs.AI"}],
                "published": "2024-01-01T00:00:00Z",
                "updated": "2024-01-02T00:00:00Z",
                "doi": "10.1000/test",
            }
        )

        self.assertEqual(item["external_id"], "2401.12345")
        self.assertEqual(item["title"], "Test paper")
        self.assertEqual(item["domain"], ["cs.AI"])
        self.assertEqual(item["doi"], "10.1000/test")


class ParserRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_registry_contains_implemented_and_pending_parser_slots(self):
        self.assertIsInstance(PARSER_REGISTRY["huggingface"], HuggingFaceAdapter)
        self.assertIsInstance(PARSER_REGISTRY["reddit"], RedditAdapter)

        self.assertIsInstance(PARSER_REGISTRY["arxiv"], ArxivAdapter)
        self.assertTrue(get_parser_spec("arxiv").implemented)
        self.assertTrue(get_parser_spec("arxiv").is_active)

        for code in ("pypi",):
            with self.subTest(parser=code):
                spec = get_parser_spec(code)
                parser = PARSER_REGISTRY[code]

                self.assertIsNotNone(spec)
                self.assertFalse(spec.implemented)
                self.assertFalse(spec.is_active)
                self.assertIsInstance(parser, PendingParserAdapter)
                with self.assertRaisesRegex(NotImplementedError, "pending"):
                    await parser.fetch(datetime(2024, 1, 1), datetime(2024, 2, 1))

        spec = get_parser_spec("github")
        self.assertIsNotNone(spec)
        self.assertTrue(spec.implemented)
        self.assertTrue(spec.is_active)
        from parsers.adapters import GitHubAdapter
        self.assertIsInstance(PARSER_REGISTRY["github"], GitHubAdapter)

    async def test_pending_parser_normalizes_common_fields(self):
        parser = PendingParserAdapter("github", "GitHub")
        normalized = parser.normalize(
            {
                "stars": 10,
                "created_at_source": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "updated_at_source": datetime(2024, 1, 2, tzinfo=timezone.utc),
            }
        )

        self.assertEqual(normalized["popularity_metric"], 10)
        self.assertIsNone(normalized["created_at_source"].tzinfo)
        self.assertEqual(normalized["domain"], [])
        self.assertEqual(normalized["tags"], [])

    async def test_source_payloads_follow_registry_specs(self):
        payloads = {payload["code"]: payload for payload in get_source_payloads()}

        self.assertEqual(set(payloads), {"huggingface", "reddit", "github", "arxiv", "pypi"})
        self.assertTrue(payloads["huggingface"]["is_active"])
        self.assertTrue(payloads["reddit"]["is_active"])
        self.assertTrue(payloads["github"]["is_active"])
        self.assertTrue(payloads["arxiv"]["is_active"])
        self.assertFalse(payloads["pypi"]["is_active"])


if __name__ == "__main__":
    unittest.main()
