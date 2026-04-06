import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError
from pymongo import MongoClient

from app.core.config import settings
from app.models.domain import Option, Question


def _default_input_path() -> Path:
    for candidate in (Path("scripts/exam.json"), Path("scripts/exam.jsonl")):
        if candidate.exists():
            return candidate
    return Path("scripts/exam.json")


DEFAULT_INPUT = _default_input_path()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the questions collection used by the assessment flow."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT,
        help="JSON file containing the exam questions. Defaults to scripts/exam.json.",
    )
    parser.add_argument(
        "--mongo-uri", default=settings.mongo_uri, help="MongoDB connection URI"
    )
    parser.add_argument(
        "--db-name", default=settings.mongo_db_name, help="MongoDB database name"
    )
    parser.add_argument(
        "--collection",
        default="questions",
        help="MongoDB collection name. Defaults to the assessment lookup collection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the mapped questions without writing to MongoDB.",
    )
    return parser.parse_args()


def _option_items(raw_options: dict[str, str], row_number: int) -> list[Option]:
    if not isinstance(raw_options, dict) or not raw_options:
        raise ValueError(
            f"Question {row_number}: alternativas must be a non-empty object."
        )
    return [
        Option(key=key.upper(), text=value.strip())
        for key, value in raw_options.items()
    ]


def _build_row(raw_item: dict, index: int) -> Question:
    try:
        number = int(raw_item["numero"])
        category = str(raw_item["categoria"]).strip()
        statement = str(raw_item["pergunta"]).strip()
        options = _option_items(raw_item["alternativas"], number)
        correct_option = str(raw_item["resposta_correta"]).strip().upper()
        tags = [str(t).strip() for t in raw_item.get("tags", [])]
    except KeyError as exc:
        raise ValueError(
            f"Question entry #{index + 1} is missing required field {exc.args[0]!r}."
        ) from exc

    try:
        question = Question(
            number=number,
            statement=statement,
            options=options,
            correct_option=correct_option,
            category=category,
            tags=tags,
        )
    except ValidationError as exc:
        raise ValueError(f"Question {number}: invalid payload: {exc}") from exc

    option_keys = {option.key for option in question.options}
    if question.correct_option not in option_keys:
        raise ValueError(
            f"Question {number}: resposta_correta {question.correct_option!r} "
            f"does not match available options {sorted(option_keys)}."
        )

    return question


def load_rows(json_path: Path) -> list[Question]:
    if not json_path.exists():
        raise FileNotFoundError(f"Input file not found: {json_path}")

    raw_text = json_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        raise ValueError("Exam file is empty.")

    try:
        raw_content = json.loads(raw_text)
    except json.JSONDecodeError:
        raw_content = []
        for line_number, line in enumerate(raw_text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw_content.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc.msg}"
                ) from exc

    if not isinstance(raw_content, list):
        raise ValueError("Exam JSON must contain a top-level array of questions.")

    rows = [_build_row(item, index) for index, item in enumerate(raw_content)]

    numbers = [row.number for row in rows]
    duplicates = sorted({number for number in numbers if numbers.count(number) > 1})
    if duplicates:
        raise ValueError(f"Duplicate question numbers found: {duplicates}")

    return rows


def seed_questions(
    *, rows: list[Question], mongo_uri: str, db_name: str, collection_name: str
) -> tuple[int, int]:
    inserted = 0
    updated = 0
    now = datetime.now(UTC)

    with MongoClient(mongo_uri) as client:
        collection = client[db_name][collection_name]
        for row in rows:
            document = {
                "number": row.number,
                "statement": row.statement,
                "options": [option.model_dump() for option in row.options],
                "correct_option": row.correct_option,
                "category": row.category.value,
                "tags": row.tags,
                "updated_at": now,
            }
            result = collection.update_one(
                {"number": row.number},
                {"$set": document, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            if result.upserted_id is not None:
                inserted += 1
            elif result.matched_count:
                updated += 1

    return inserted, updated


def main() -> int:
    args = parse_args()
    rows = load_rows(args.input)

    if args.dry_run:
        for row in rows:
            print(f"{row.number}: {row.category} - {row.statement}")
        print(f"Validated {len(rows)} question(s).")
        return 0

    inserted, updated = seed_questions(
        rows=rows,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        collection_name=args.collection,
    )
    print(
        f"Seed completed for collection '{args.collection}': "
        f"{len(rows)} question(s), {inserted} inserted, {updated} updated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
