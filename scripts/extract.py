from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pymongo import MongoClient


SCHEMA_VERSION = "v1"


def mask_cpf(cpf: str) -> str:
    digits = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(digits) != 11:
        return "***"
    return f"***.***.***-{digits[-2:]}"


def fetch_collection_or_fail(db, name: str):
    collections = db.list_collection_names()
    if name not in collections:
        raise RuntimeError(f"Missing collection: {name}")
    return db[name]


def build_rows(db) -> list[dict]:
    students = {str(s["_id"]): s for s in fetch_collection_or_fail(db, "students").find({})}
    questions = {str(q["_id"]): q for q in fetch_collection_or_fail(db, "questions").find({})}
    assessments = list(fetch_collection_or_fail(db, "assessments").find({}))
    answers = list(fetch_collection_or_fail(db, "answers").find({}))

    answers_by_assessment = {}
    for ans in answers:
        answers_by_assessment.setdefault(str(ans["assessment_id"]), []).append(ans)

    rows = []
    for assessment in assessments:
        sid = str(assessment["student_id"])
        student = students.get(sid)
        if not student:
            continue

        per_answers = answers_by_assessment.get(str(assessment["_id"]), [])
        answer_map = {str(a["question_id"]): a["selected_option"] for a in per_answers}

        correct = 0
        total_answered = 0
        for qid, q in questions.items():
            selected = answer_map.get(qid)
            if selected is None:
                continue
            total_answered += 1
            if selected == q.get("correct_option"):
                correct += 1

        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "assessment_id": str(assessment["_id"]),
                "student_id": sid,
                "cpf_masked": mask_cpf(student.get("cpf", "")),
                "status": assessment.get("status"),
                "started_at": assessment.get("started_at"),
                "completed_at": assessment.get("completed_at"),
                "answered_count": total_answered,
                "correct_count": correct,
            }
        )

    return rows


def run(uri: str, database: str, output_path: Path) -> int:
    import pandas as pd

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = MongoClient(uri)
    db = client[database]

    try:
        rows = build_rows(db)
    except RuntimeError as exc:
        logging.error("Extraction failed: %s", exc)
        return 2

    columns = [
        "schema_version",
        "assessment_id",
        "student_id",
        "cpf_masked",
        "status",
        "started_at",
        "completed_at",
        "answered_count",
        "correct_count",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        logging.warning("No rows found. Writing header-only CSV.")
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)
        return 0

    pd.DataFrame(rows, columns=columns).to_csv(output_path, index=False)
    logging.info("Wrote %s rows to %s", len(rows), output_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Kodie assessment dataset")
    parser.add_argument("--uri", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", default="output/kodie_dataset.csv")
    args = parser.parse_args()

    return run(args.uri, args.database, Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
