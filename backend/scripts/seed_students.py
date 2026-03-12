import argparse
import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path

from pymongo import MongoClient

from app.core.config import settings
from app.core.utils import is_valid_cpf, normalize_cpf


@dataclass
class StudentSeedRow:
    cpf: str
    name: str
    birth_date: date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the students collection used by the authentication flow."
    )
    parser.add_argument("input", type=Path, help="CSV file with columns: cpf,name,birth_date")
    parser.add_argument("--mongo-uri", default=settings.mongo_uri, help="MongoDB connection URI")
    parser.add_argument("--db-name", default=settings.mongo_db_name, help="MongoDB database name")
    parser.add_argument(
        "--collection",
        default="students",
        help="MongoDB collection name. Defaults to the auth lookup collection.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the rows without writing to MongoDB.",
    )
    return parser.parse_args()


def parse_birth_date(raw_value: str, row_number: int) -> date:
    try:
        return date.fromisoformat(raw_value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Row {row_number}: invalid birth_date {raw_value!r}. Expected format YYYY-MM-DD."
        ) from exc


def load_rows(csv_path: Path) -> list[StudentSeedRow]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"cpf", "name", "birth_date"}
        if reader.fieldnames is None:
            raise ValueError("CSV file must include a header row with cpf,name,birth_date.")

        missing = expected.difference(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV file is missing required columns: {', '.join(sorted(missing))}")

        rows: list[StudentSeedRow] = []
        for row_number, raw_row in enumerate(reader, start=2):
            cpf = normalize_cpf((raw_row.get("cpf") or "").strip())
            name = (raw_row.get("name") or "").strip()
            birth_date = parse_birth_date(raw_row.get("birth_date") or "", row_number)

            if not cpf:
                raise ValueError(f"Row {row_number}: cpf is required.")
            if not is_valid_cpf(cpf):
                raise ValueError(f"Row {row_number}: invalid CPF {raw_row.get('cpf')!r}.")
            if not name:
                raise ValueError(f"Row {row_number}: name is required.")

            rows.append(StudentSeedRow(cpf=cpf, name=name, birth_date=birth_date))

    return rows


def to_mongo_birth_date(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def seed_students(*, rows: list[StudentSeedRow], mongo_uri: str, db_name: str, collection_name: str) -> tuple[int, int]:
    inserted = 0
    updated = 0
    now = datetime.now(UTC)

    with MongoClient(mongo_uri) as client:
        collection = client[db_name][collection_name]
        for row in rows:
            document = {
                "cpf": row.cpf,
                "name": row.name,
                "birth_date": to_mongo_birth_date(row.birth_date),
                "updated_at": now,
            }
            result = collection.update_one(
                {"cpf": row.cpf},
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
            print(f"{row.cpf},{row.name},{row.birth_date.isoformat()}")
        print(f"Validated {len(rows)} row(s).")
        return 0

    inserted, updated = seed_students(
        rows=rows,
        mongo_uri=args.mongo_uri,
        db_name=args.db_name,
        collection_name=args.collection,
    )
    print(
        f"Seed completed for collection '{args.collection}': "
        f"{len(rows)} row(s), {inserted} inserted, {updated} updated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
