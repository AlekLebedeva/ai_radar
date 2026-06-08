from uuid import uuid4
from datetime import datetime

from ai_radar_reddit_hg.parsers.parse import HuggingFaceModelsParser
from shemas.parserTask import ParserTask


def main() -> None:
    parser = HuggingFaceModelsParser()

    task = ParserTask(
        task_id=uuid4(),
        parser_name="huggingface_models_all_categories",
        date_from=None,
        date_to=None,
        source_type="huggingface",
        filters={"search": ""},
        batch_size=50,
        max_items=100,
        parse_all_categories=True,
        delay_seconds=2.0,
        delay_between_items=0.05,
    )

    models = parser.run(task)
    print(f"Parsed models: {len(models)}")
    if models:
        print(models[0])


if __name__ == "__main__":
    main()
