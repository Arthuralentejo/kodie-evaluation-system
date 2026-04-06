from app.core.logger import build_log_message, get_logger
from app.models.api import AnalyticsResult, LevelAccuracyStat, ScoreDistributionBucket
from app.repositories.assessment_repository import AssessmentRepository

logger = get_logger("kodie.services.analytics")


class AnalyticsService:
    def __init__(self, repository: AssessmentRepository):
        self.repository = repository

    async def get_analytics(self, *, assessment_type: str | None = None) -> AnalyticsResult:
        logger.info(build_log_message("analytics_started", assessment_type=assessment_type))
        raw = await self.repository.aggregate_analytics(assessment_type=assessment_type)

        score_distribution_raw = [
            ScoreDistributionBucket(bucket=str(item["_id"]), count=item["count"])
            for item in raw.get("score_distribution_raw", [])
        ]

        # Build normalized buckets from $bucket output
        bucket_labels = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90-99", "100"]
        bucket_boundaries = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        raw_normalized = {item["_id"]: item["count"] for item in raw.get("score_distribution_normalized", [])}
        score_distribution_normalized = []
        for i, boundary in enumerate(bucket_boundaries):
            label = bucket_labels[i]
            count = raw_normalized.get(boundary, 0)
            score_distribution_normalized.append(ScoreDistributionBucket(bucket=label, count=count))
        # Handle the "100" default bucket
        if "100" in raw_normalized:
            score_distribution_normalized.append(ScoreDistributionBucket(bucket="100", count=raw_normalized["100"]))

        classification_distribution = {
            item["_id"]: item["count"]
            for item in raw.get("classification_distribution", [])
            if item["_id"] is not None
        }

        level_accuracy = [
            LevelAccuracyStat(level=item["_id"], mean_accuracy=item.get("mean_accuracy"))
            for item in raw.get("level_accuracy", [])
        ]

        result = AnalyticsResult(
            score_distribution_raw=score_distribution_raw,
            score_distribution_normalized=score_distribution_normalized,
            classification_distribution=classification_distribution,
            level_accuracy=level_accuracy,
            assessment_type_filter=assessment_type,
        )
        logger.info(
            build_log_message(
                "analytics_completed",
                assessment_type=assessment_type,
                raw_bucket_count=len(score_distribution_raw),
                normalized_bucket_count=len(score_distribution_normalized),
                classification_bucket_count=len(classification_distribution),
                level_accuracy_count=len(level_accuracy),
            )
        )
        return result
