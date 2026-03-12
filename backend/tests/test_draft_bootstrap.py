from datetime import UTC, datetime

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.services import auth_service


class _AssessmentsRace:
    def __init__(self, expected_doc):
        self.expected_doc = expected_doc

    async def find_one_and_update(self, *args, **kwargs):
        raise DuplicateKeyError("duplicate")

    async def find_one(self, query):
        if query.get("status") == "DRAFT":
            return self.expected_doc
        return None


@pytest.mark.asyncio
async def test_draft_bootstrap_race_recovers_after_duplicate(monkeypatch):
    student_id = ObjectId()
    draft_doc = {
        "_id": ObjectId(),
        "student_id": student_id,
        "status": "DRAFT",
        "started_at": datetime.now(UTC),
        "completed_at": None,
    }

    fake = _AssessmentsRace(draft_doc)
    monkeypatch.setattr(auth_service, "assessments_collection", lambda _: fake)

    result = await auth_service._get_or_create_draft_assessment(student_id=student_id, db=object())
    assert result == draft_doc
