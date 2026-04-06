from datetime import UTC, datetime

from bson import ObjectId
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
import pytest

from app.api import deps
from app.api.routes.assessments import router as assessments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes import health as health_route
from app.core.errors import AppError


class _AuthServiceStub:
    def __init__(self):
        self.auth_response = {"token": "stub-token", "claims": {}}
        self.last_auth_call = None
        self.last_revoke_call = None

    async def authenticate_and_issue_token(self, *, cpf, birth_date, ip, request_id):
        self.last_auth_call = {
            "cpf": cpf,
            "birth_date": birth_date,
            "ip": ip,
            "request_id": request_id,
        }
        return self.auth_response

    async def revoke_token(self, *, jti, exp):
        self.last_revoke_call = {"jti": jti, "exp": exp}


class _AssessmentServiceStub:
    def __init__(self):
        self.questions_response = []
        self.submit_response = {"status": "COMPLETED", "completed_at": datetime.now(UTC).isoformat()}
        self.current_response = {"status": "NONE", "assessment_id": None, "completed_at": None}
        self.create_response = {"status": "DRAFT", "assessment_id": str(ObjectId()), "assessment_type": "iniciante"}
        self.last_get_current_call = None
        self.last_create_call = None
        self.last_get_questions_call = None
        self.last_upsert_answer_call = None
        self.last_submit_call = None

    async def get_current_assessment(self, *, student_id):
        self.last_get_current_call = {"student_id": student_id}
        return self.current_response

    async def create_assessment(self, *, student_id, assessment_type="iniciante"):
        self.last_create_call = {"student_id": student_id, "assessment_type": assessment_type}
        return self.create_response

    async def get_questions_for_assessment(self, *, assessment_id, quantity=None, request_id=None):
        self.last_get_questions_call = {
            "assessment_id": assessment_id,
            "quantity": quantity,
            "request_id": request_id,
        }
        return self.questions_response

    async def upsert_answer(self, *, assessment_id, question_id, selected_option, request_id=None):
        self.last_upsert_answer_call = {
            "assessment_id": assessment_id,
            "question_id": question_id,
            "selected_option": selected_option,
            "request_id": request_id,
        }

    async def submit_assessment(self, *, assessment_id, request_id=None):
        self.last_submit_call = {"assessment_id": assessment_id, "request_id": request_id}
        return self.submit_response


@pytest.fixture
def http_app() -> FastAPI:
    test_app = FastAPI()
    test_app.state.auth_service = _AuthServiceStub()
    test_app.state.assessment_service = _AssessmentServiceStub()

    @test_app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id", "test-request-id")
        request.state.auth_service = test_app.state.auth_service
        request.state.assessment_service = test_app.state.assessment_service
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @test_app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        details = dict(exc.details)
        retry_after = details.pop("retry_after", None)
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
                "details": details or {},
            },
        )
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
        return response

    @test_app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "request_id": request.state.request_id,
                "details": {"errors": jsonable_encoder(exc.errors())},
            },
        )

    test_app.include_router(auth_router)
    test_app.include_router(assessments_router)
    test_app.include_router(health_router)

    return test_app


@pytest.fixture
async def client(http_app: FastAPI):
    transport = ASGITransport(app=http_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _override_auth(student_id: str, assessment_id: str):
    async def _inner():
        return deps.AuthContext(student_id=student_id, jti="j1", exp=9999999999)

    return _inner


@pytest.mark.asyncio
async def test_post_auth_validation_error_envelope(client):
    response = await client.post("/auth", json={"cpf": "123", "birth_date": "2000-01-01"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["request_id"]


@pytest.mark.asyncio
async def test_post_auth_success(client, monkeypatch):
    client._transport.app.state.auth_service.auth_response = {
        "token": "tkn",
        "claims": {},
    }

    response = await client.post("/auth", json={"cpf": "52998224725", "birth_date": "2000-01-01"})

    assert response.status_code == 200
    assert response.json()["token"] == "tkn"
    assert client._transport.app.state.auth_service.last_auth_call["cpf"] == "52998224725"


@pytest.mark.asyncio
async def test_get_current_assessment_http_success(http_app, client):
    assessment_id = ObjectId()
    student_id = ObjectId()

    http_app.dependency_overrides[deps.get_auth_context] = _override_auth(str(student_id), str(assessment_id))
    http_app.state.assessment_service.current_response = {
        "status": "DRAFT",
        "assessment_id": str(assessment_id),
        "completed_at": None,
    }

    response = await client.get("/assessments/current", headers={"Authorization": "Bearer any"})

    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"
    assert http_app.state.assessment_service.last_get_current_call == {"student_id": str(student_id)}


@pytest.mark.asyncio
async def test_create_assessment_http_success(http_app, client):
    assessment_id = ObjectId()
    student_id = ObjectId()

    http_app.dependency_overrides[deps.get_auth_context] = _override_auth(str(student_id), str(assessment_id))

    response = await client.post("/assessments", headers={"Authorization": "Bearer any"}, json={})

    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"
    assert http_app.state.assessment_service.last_create_call == {"student_id": str(student_id), "assessment_type": "iniciante"}


@pytest.mark.asyncio
async def test_get_questions_http_success(http_app, client):
    assessment_id = ObjectId()
    question_id = ObjectId()
    student_id = ObjectId()

    http_app.dependency_overrides[deps.get_auth_context] = _override_auth(str(student_id), str(assessment_id))
    http_app.state.assessment_service.questions_response = [
        {"id": str(question_id), "statement": "Q", "options": [{"key": "A", "text": "a"}], "selected_option": "A"}
    ]

    response = await client.get(f"/assessments/{assessment_id}/questions", headers={"Authorization": "Bearer any"})

    assert response.status_code == 200
    assert response.json()[0]["selected_option"] == "A"
    assert http_app.state.assessment_service.last_get_questions_call == {
        "assessment_id": str(assessment_id),
        "quantity": 20,
        "request_id": "test-request-id",
    }


@pytest.mark.asyncio
async def test_get_questions_http_passes_quantity(http_app, client):
    assessment_id = ObjectId()
    student_id = ObjectId()

    http_app.dependency_overrides[deps.get_auth_context] = _override_auth(str(student_id), str(assessment_id))
    http_app.state.assessment_service.questions_response = []

    response = await client.get(
        f"/assessments/{assessment_id}/questions?quantity=2",
        headers={"Authorization": "Bearer any"},
    )

    assert response.status_code == 200
    assert http_app.state.assessment_service.last_get_questions_call == {
        "assessment_id": str(assessment_id),
        "quantity": 2,
        "request_id": "test-request-id",
    }


@pytest.mark.asyncio
async def test_submit_http_uses_assessment_service(http_app, client):
    assessment_id = ObjectId()
    student_id = ObjectId()

    http_app.dependency_overrides[deps.get_auth_context] = _override_auth(str(student_id), str(assessment_id))

    first = await client.post(f"/assessments/{assessment_id}/submit", headers={"Authorization": "Bearer any"})
    second = await client.post(f"/assessments/{assessment_id}/submit", headers={"Authorization": "Bearer any"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["completed_at"] == second.json()["completed_at"]
    assert http_app.state.assessment_service.last_submit_call == {
        "assessment_id": str(assessment_id),
        "request_id": "test-request-id",
    }


@pytest.mark.asyncio
async def test_assessment_route_requires_token(client):
    response = await client.get(f"/assessments/{ObjectId()}/questions")

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "MISSING_TOKEN"
    assert body["request_id"]


@pytest.mark.asyncio
async def test_live_returns_ok(client):
    response = await client.get("/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_dependency_status_and_timing(client, monkeypatch):
    async def _ping_db() -> None:
        return None

    monkeypatch.setattr(health_route, "ping_db", _ping_db)

    response = await client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["mongodb"]["status"] == "ok"
    assert isinstance(body["checks"]["mongodb"]["time_ms"], float)
    assert body["checks"]["mongodb"]["time_ms"] >= 0


@pytest.mark.asyncio
async def test_ready_returns_503_when_mongodb_is_unavailable(client, monkeypatch):
    async def _ping_db() -> None:
        raise RuntimeError("mongo unavailable")

    monkeypatch.setattr(health_route, "ping_db", _ping_db)

    response = await client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["checks"]["mongodb"]["status"] == "error"
    assert isinstance(body["checks"]["mongodb"]["time_ms"], float)
    assert body["checks"]["mongodb"]["time_ms"] >= 0


# ── Admin API tests ──────────────────────────────────────────────────────────

from app.api.routes.admin import router as admin_router
from app.core.config import settings
from app.models.api import AnalyticsResult, RankingPage


class _RankingServiceStub:
    async def rank_by_type(self, *, assessment_type, page=1, page_size=20):
        return RankingPage(entries=[], total=0, page=page, page_size=page_size)

    async def rank_global(self, *, page=1, page_size=20):
        return RankingPage(entries=[], total=0, page=page, page_size=page_size)


class _AnalyticsServiceStub:
    async def get_analytics(self, *, assessment_type=None):
        return AnalyticsResult(
            score_distribution_raw=[],
            score_distribution_normalized=[],
            classification_distribution={},
            level_accuracy=[],
            assessment_type_filter=assessment_type,
        )


class _RepoStub:
    def __init__(self, docs=None):
        self._docs = docs or []

    async def list_completed_assessments(self, *, assessment_type=None, classification_value=None, page=1, page_size=20):
        return self._docs, len(self._docs)

    async def find_assessment_by_id(self, *, assessment_id):
        return None


class _AssessmentServiceWithRepo:
    """Wraps a stub repo so admin router can access request.state.assessment_service.repository."""
    def __init__(self, repo):
        self.repository = repo


@pytest.fixture
def admin_http_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(settings, "admin_token", "test-admin-token")

    test_app = FastAPI()
    test_app.state.auth_service = _AuthServiceStub()
    repo = _RepoStub()
    test_app.state.assessment_service = _AssessmentServiceWithRepo(repo)
    test_app.state.ranking_service = _RankingServiceStub()
    test_app.state.analytics_service = _AnalyticsServiceStub()

    @test_app.middleware("http")
    async def state_middleware(request: Request, call_next):
        request.state.request_id = "test-request-id"
        request.state.auth_service = test_app.state.auth_service
        request.state.assessment_service = test_app.state.assessment_service
        request.state.assessment_repository = repo
        request.state.ranking_service = test_app.state.ranking_service
        request.state.analytics_service = test_app.state.analytics_service
        return await call_next(request)

    @test_app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        details = dict(exc.details)
        details.pop("retry_after", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "request_id": "test-request-id", "details": details or {}},
        )

    test_app.include_router(admin_router)
    return test_app


@pytest.fixture
async def admin_client(admin_http_app: FastAPI):
    transport = ASGITransport(app=admin_http_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_admin_results_returns_401_without_token(admin_client):
    response = await admin_client.get("/admin/results")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_admin_results_returns_403_with_wrong_token(admin_client):
    response = await admin_client.get("/admin/results", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_admin_results_returns_200_with_correct_token(admin_client):
    response = await admin_client.get("/admin/results", headers={"Authorization": "Bearer test-admin-token"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_result_detail_returns_404_for_unknown_assessment(admin_client):
    unknown_id = str(ObjectId())
    response = await admin_client.get(
        f"/admin/results/{unknown_id}",
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ASSESSMENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_admin_ranking_by_type_requires_assessment_type(admin_client):
    response = await admin_client.get(
        "/admin/ranking/by-type",
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_ranking_by_type_returns_200_with_param(admin_client):
    response = await admin_client.get(
        "/admin/ranking/by-type?assessment_type=iniciante",
        headers={"Authorization": "Bearer test-admin-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert body["total"] == 0
