from dataclasses import dataclass, field
from typing import Callable

from parsers.base import BaseParser


@dataclass(frozen=True)
class ParserSpec:
    code: str
    name: str
    api_base_url: str
    api_doc_url: str = ""
    auth_type: str = "none"
    rate_limit: dict[str, int] = field(default_factory=dict)
    is_active: bool = True
    implemented: bool = True


PARSER_SPECS: tuple[ParserSpec, ...] = (
    ParserSpec(
        code="huggingface",
        name="Hugging Face",
        api_base_url="https://huggingface.co/api",
        api_doc_url="https://huggingface.co/docs/hub/api",
        auth_type="token_header",
        rate_limit={"rpm": 100},
    ),
    ParserSpec(
        code="reddit",
        name="Reddit",
        api_base_url="https://oauth.reddit.com",
        api_doc_url="https://www.reddit.com/dev/api",
        auth_type="oauth2",
        rate_limit={"rpm": 60},
    ),
    ParserSpec(
        code="github",
        name="GitHub",
        api_base_url="https://api.github.com",
        api_doc_url="https://docs.github.com/en/rest",
        auth_type="token_header",
        rate_limit={"rpm": 30},
        is_active=False,
        implemented=False,
    ),
    ParserSpec(
        code="arxiv",
        name="arXiv",
        api_base_url="http://export.arxiv.org/api",
        api_doc_url="https://arxiv.org/help/api",
        rate_limit={"rpm": 20},
        is_active=False,
        implemented=False,
    ),
    ParserSpec(
        code="pypi",
        name="PyPI",
        api_base_url="https://pypi.org/pypi",
        api_doc_url="https://docs.pypi.org/api",
        rate_limit={"rpm": 60},
        is_active=False,
        implemented=False,
    ),
)


def _build_parser_factory(spec: ParserSpec) -> Callable[[], BaseParser]:
    if spec.code == "huggingface":
        from parsers.adapters import HuggingFaceAdapter

        return HuggingFaceAdapter
    if spec.code == "reddit":
        from parsers.adapters import RedditAdapter

        return RedditAdapter

    def factory() -> BaseParser:
        from parsers.pending import PendingParserAdapter

        return PendingParserAdapter(
            spec.code,
            spec.name,
            spec.api_base_url,
            message=f"{spec.name} parser is registered as pending. Implement its adapter before running tasks.",
        )

    return factory


PARSER_FACTORIES: dict[str, Callable[[], BaseParser]] = {
    spec.code: _build_parser_factory(spec) for spec in PARSER_SPECS
}

PARSER_REGISTRY: dict[str, BaseParser] = {
    code: factory() for code, factory in PARSER_FACTORIES.items()
}


def get_parser(code: str) -> BaseParser | None:
    return PARSER_REGISTRY.get(code)


def get_parser_spec(code: str) -> ParserSpec | None:
    return next((spec for spec in PARSER_SPECS if spec.code == code), None)


def get_source_payloads() -> list[dict[str, object]]:
    return [
        {
            "id": spec.code,
            "name": spec.name,
            "code": spec.code,
            "api_base_url": spec.api_base_url,
            "api_doc_url": spec.api_doc_url,
            "auth_type": spec.auth_type,
            "rate_limit": spec.rate_limit,
            "is_active": spec.is_active,
        }
        for spec in PARSER_SPECS
    ]
