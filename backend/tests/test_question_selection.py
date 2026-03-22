from bson import ObjectId

from app.services.question_selection import build_assigned_question_ids


def test_build_assigned_question_ids_caps_assessment_size():
    docs = []
    categories = (["iniciante"] * 12) + (["junior"] * 10) + (["pleno"] * 6) + (["senior"] * 4)

    for number, category in enumerate(categories, start=1):
        docs.append({"_id": ObjectId(), "number": number, "category": category})

    assigned_ids = build_assigned_question_ids(docs)

    assert len(assigned_ids) == 20
