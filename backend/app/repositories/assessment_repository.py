from datetime import UTC, datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.core.logger import build_log_message, get_logger, hash_identifier

logger = get_logger("kodie.repositories.assessment")


def _ensure_utc(doc: dict | None) -> dict | None:
    """Attach UTC tzinfo to offset-naive datetime fields that MongoDB strips on round-trip."""
    if doc is None:
        return None
    for field in ("started_at", "completed_at"):
        val = doc.get(field)
        if isinstance(val, datetime) and val.tzinfo is None:
            doc[field] = val.replace(tzinfo=UTC)
    return doc


class AssessmentRepository:
    def __init__(self, collection, questions_collection):
        self.collection = collection
        self.questions_collection = questions_collection

    async def find_assessment_by_id(self, *, assessment_id: ObjectId) -> dict | None:
        result = _ensure_utc(await self.collection.find_one({"_id": assessment_id}))
        logger.info(
            build_log_message(
                "assessment_lookup_completed",
                assessment_id=str(assessment_id),
                found=result is not None,
                status=result.get("status") if result else None,
                archived=result.get("archived") if result else None,
            )
        )
        return result

    async def find_questions_by_ids(self, *, question_ids: list[ObjectId]) -> list[dict]:
        results = await self.questions_collection.find({"_id": {"$in": question_ids}}).to_list(length=None)
        logger.info(
            build_log_message(
                "questions_lookup_by_ids_completed",
                requested_count=len(question_ids),
                returned_count=len(results),
            )
        )
        return results

    async def find_question_by_id(self, *, question_id: ObjectId) -> dict | None:
        result = await self.questions_collection.find_one({"_id": question_id})
        logger.info(build_log_message("question_lookup_completed", question_id=str(question_id), found=result is not None))
        return result

    async def find_draft_assessment_by_student(self, *, student_id: str) -> dict | None:
        result = await self.collection.find_one(
            {"student_id": student_id, "status": "DRAFT", "archived": False}
        )
        logger.info(
            build_log_message(
                "draft_assessment_lookup_completed",
                student_ref=hash_identifier(student_id),
                found=result is not None,
                assessment_id=str(result["_id"]) if result else None,
            )
        )
        return result

    async def find_active_assessment_by_student(self, *, student_id: str) -> dict | None:
        result = await self.collection.find_one({"student_id": student_id, "archived": False})
        logger.info(
            build_log_message(
                "active_assessment_lookup_completed",
                student_ref=hash_identifier(student_id),
                found=result is not None,
                assessment_id=str(result["_id"]) if result else None,
                status=result.get("status") if result else None,
            )
        )
        return result

    async def find_all_completed_assessments_by_student(self, *, student_id: str) -> list[dict]:
        # includes archived — full history
        results = await self.collection.find(
            {"student_id": student_id, "status": "COMPLETED"},
            sort=[("completed_at", -1)],
        ).to_list(length=None)
        logger.info(
            build_log_message(
                "completed_assessments_history_lookup_completed",
                student_ref=hash_identifier(student_id),
                returned_count=len(results),
            )
        )
        return results

    async def archive_assessment(self, *, assessment_id: ObjectId) -> None:
        await self.collection.update_one(
            {"_id": assessment_id},
            {"$set": {"archived": True}},
        )
        logger.info(build_log_message("assessment_archived", assessment_id=str(assessment_id)))

    async def list_questions_for_level(self, *, level: str) -> list[dict]:
        results = await self.questions_collection.find(
            {"category": level},
            {"_id": 1, "number": 1, "category": 1},
        ).to_list(length=None)
        logger.info(build_log_message("questions_for_level_listed", assessment_type=level, returned_count=len(results)))
        return results

    async def list_questions_for_geral(self) -> list[dict]:
        results = await self.questions_collection.find(
            {},
            {"_id": 1, "number": 1, "category": 1},
        ).to_list(length=None)
        logger.info(build_log_message("questions_for_geral_listed", returned_count=len(results)))
        return results

    async def create_assessment(
        self,
        *,
        student_id: str,
        assigned_question_ids: list[ObjectId],
        assessment_type: str,
        now: datetime,
    ) -> dict:
        document = {
            "student_id": student_id,
            "assigned_question_ids": assigned_question_ids,
            "answers": [],
            "status": "DRAFT",
            "assessment_type": assessment_type,
            "archived": False,
            "started_at": now,
            "completed_at": None,
        }
        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        logger.info(
            build_log_message(
                "assessment_created",
                assessment_id=str(result.inserted_id),
                student_ref=hash_identifier(student_id),
                assessment_type=assessment_type,
                assigned_count=len(assigned_question_ids),
                started_at=now,
            )
        )
        return document

    async def update_assessment_answers(self, *, assessment_id: ObjectId, answers: list[dict]) -> None:
        await self.collection.update_one(
            {"_id": assessment_id},
            {"$set": {"answers": answers}},
        )
        logger.info(
            build_log_message(
                "assessment_answers_updated",
                assessment_id=str(assessment_id),
                answer_count=len(answers),
            )
        )

    async def complete_assessment(
        self,
        *,
        assessment_id: ObjectId,
        completed_at: datetime,
        evaluation_result: dict | None = None,
    ) -> dict | None:
        update = {"status": "COMPLETED", "completed_at": completed_at}
        if evaluation_result is not None:
            update["evaluation_result"] = evaluation_result
        result = _ensure_utc(await self.collection.find_one_and_update(
            {"_id": assessment_id, "status": "DRAFT"},
            {"$set": update},
            return_document=ReturnDocument.AFTER,
        ))
        logger.info(
            build_log_message(
                "assessment_completion_update_completed",
                assessment_id=str(assessment_id),
                updated=result is not None,
                completed_at=completed_at,
                has_evaluation_result=evaluation_result is not None,
            )
        )
        return result

    async def list_completed_assessments(
        self,
        *,
        assessment_type: str | None = None,
        classification_value: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        query: dict = {"status": "COMPLETED"}
        if assessment_type:
            query["assessment_type"] = assessment_type
        if classification_value:
            query["evaluation_result.classification_value"] = classification_value
        total = await self.collection.count_documents(query)
        skip = (page - 1) * page_size
        docs = await self.collection.find(query, sort=[("completed_at", -1)]).skip(skip).limit(page_size).to_list(length=None)
        logger.info(
            build_log_message(
                "completed_assessments_listed",
                assessment_type=assessment_type,
                classification_value=classification_value,
                page=page,
                page_size=page_size,
                total=total,
                returned_count=len(docs),
            )
        )
        return docs, total

    async def aggregate_analytics(self, *, assessment_type: str | None = None) -> dict:
        match_stage: dict = {"status": "COMPLETED", "evaluation_result": {"$exists": True}}
        if assessment_type:
            match_stage["assessment_type"] = assessment_type

        pipeline = [
            {"$match": match_stage},
            {"$facet": {
                "score_distribution_raw": [
                    {"$group": {"_id": "$evaluation_result.score_total", "count": {"$sum": 1}}},
                    {"$sort": {"_id": 1}},
                ],
                "score_distribution_normalized": [
                    {"$bucket": {
                        "groupBy": "$evaluation_result.score_percent",
                        "boundaries": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
                        "default": "100",
                        "output": {"count": {"$sum": 1}},
                    }},
                ],
                "classification_distribution": [
                    {"$group": {"_id": "$evaluation_result.classification_value", "count": {"$sum": 1}}},
                ],
                "level_accuracy": [
                    {"$project": {
                        "levels": {"$objectToArray": "$evaluation_result.performance_by_level"}
                    }},
                    {"$unwind": "$levels"},
                    {"$match": {"levels.v.accuracy": {"$ne": None}}},
                    {"$group": {
                        "_id": "$levels.k",
                        "mean_accuracy": {"$avg": "$levels.v.accuracy"},
                    }},
                    {"$sort": {"_id": 1}},
                ],
            }},
        ]
        results = await self.collection.aggregate(pipeline).to_list(length=1)
        result = results[0] if results else {}
        logger.info(
            build_log_message(
                "assessment_analytics_aggregated",
                assessment_type=assessment_type,
                has_result=bool(result),
            )
        )
        return result

    async def list_completed_assessments_ranked(
        self,
        *,
        assessment_type: str | None = None,
        sort_by: str = "by_type",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        query: dict = {"status": "COMPLETED", "evaluation_result": {"$exists": True}}
        if assessment_type:
            query["assessment_type"] = assessment_type

        if sort_by == "global":
            sort = [
                ("evaluation_result.score_percent", -1),
                ("evaluation_result.score_total", -1),
                ("evaluation_result.duration_seconds", 1),
                ("completed_at", 1),
            ]
        else:
            sort = [
                ("evaluation_result.score_total", -1),
                ("evaluation_result.duration_seconds", 1),
                ("completed_at", 1),
            ]

        total = await self.collection.count_documents(query)
        skip = (page - 1) * page_size
        docs = await self.collection.find(query, sort=sort).skip(skip).limit(page_size).to_list(length=None)
        logger.info(
            build_log_message(
                "completed_assessments_ranked",
                assessment_type=assessment_type,
                sort_by=sort_by,
                page=page,
                page_size=page_size,
                total=total,
                returned_count=len(docs),
            )
        )
        return docs, total
