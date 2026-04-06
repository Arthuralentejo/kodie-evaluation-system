from app.core.logger import build_log_message, get_logger
from app.models.api import RankingEntry, RankingPage
from app.repositories.assessment_repository import AssessmentRepository

logger = get_logger("kodie.services.ranking")


class RankingService:
    def __init__(self, repository: AssessmentRepository):
        self.repository = repository

    async def rank_by_type(self, *, assessment_type: str, page: int = 1, page_size: int = 20) -> RankingPage:
        logger.info(
            build_log_message(
                "ranking_by_type_started",
                assessment_type=assessment_type,
                page=page,
                page_size=page_size,
            )
        )
        docs, total = await self.repository.list_completed_assessments_ranked(
            assessment_type=assessment_type, sort_by="by_type", page=page, page_size=page_size
        )
        offset = (page - 1) * page_size
        entries = []
        for i, doc in enumerate(docs):
            er = doc.get("evaluation_result") or {}
            entries.append(RankingEntry(
                rank=offset + i + 1,
                assessment_id=str(doc["_id"]),
                student_id=doc.get("student_id", ""),
                assessment_type=doc.get("assessment_type"),
                score_total=er.get("score_total", 0),
                score_max=er.get("score_max", 0),
                score_percent=er.get("score_percent", 0.0),
                classification_value=er.get("classification_value"),
                duration_seconds=er.get("duration_seconds", 0),
                completed_at=doc["completed_at"].isoformat() if doc.get("completed_at") else "",
            ))
        result = RankingPage(entries=entries, total=total, page=page, page_size=page_size)
        logger.info(
            build_log_message(
                "ranking_by_type_completed",
                assessment_type=assessment_type,
                page=page,
                page_size=page_size,
                total=total,
                returned_count=len(entries),
            )
        )
        return result

    async def rank_global(self, *, page: int = 1, page_size: int = 20) -> RankingPage:
        logger.info(build_log_message("ranking_global_started", page=page, page_size=page_size))
        docs, total = await self.repository.list_completed_assessments_ranked(
            sort_by="global", page=page, page_size=page_size
        )
        offset = (page - 1) * page_size
        entries = []
        for i, doc in enumerate(docs):
            er = doc.get("evaluation_result") or {}
            entries.append(RankingEntry(
                rank=offset + i + 1,
                assessment_id=str(doc["_id"]),
                student_id=doc.get("student_id", ""),
                assessment_type=doc.get("assessment_type"),
                score_total=er.get("score_total", 0),
                score_max=er.get("score_max", 0),
                score_percent=er.get("score_percent", 0.0),
                classification_value=er.get("classification_value"),
                duration_seconds=er.get("duration_seconds", 0),
                completed_at=doc["completed_at"].isoformat() if doc.get("completed_at") else "",
            ))
        result = RankingPage(entries=entries, total=total, page=page, page_size=page_size)
        logger.info(
            build_log_message(
                "ranking_global_completed",
                page=page,
                page_size=page_size,
                total=total,
                returned_count=len(entries),
            )
        )
        return result
