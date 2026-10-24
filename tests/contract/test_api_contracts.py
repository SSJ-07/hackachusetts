"""Contract tests: every endpoint's response validates against docs/contracts.md shapes."""

from tests.contract import shapes


def _assert_mock_mode(response):
    assert response.headers["X-Data-Mode"] == "mock"


# ---- /health --------------------------------------------------------------- #
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["data_mode"] == "mock"


# ---- GET /audit ------------------------------------------------------------ #
def test_audit_matches_contract(client):
    r = client.get("/audit", params={"clinic": "mock-clinic-gi", "community": "holyoke", "day": "tue"})
    assert r.status_code == 200
    _assert_mock_mode(r)
    body = shapes.Audit.model_validate(r.json())
    assert body.cells and all(c.day == "tue" for c in body.cells)
    assert all("MOCK" in s.name for s in body.sources)


def test_audit_requires_all_params(client):
    assert client.get("/audit", params={"clinic": "x", "community": "y"}).status_code == 422
    assert client.get("/audit", params={"clinic": "x", "community": "y", "day": "monday"}).status_code == 422


# ---- POST /whatif ---------------------------------------------------------- #
def test_whatif_returns_audit_shape(client):
    r = client.post("/whatif", json={"clinic": "mock-clinic-gi", "shift": {"block": "mon-08", "to": 10}})
    assert r.status_code == 200
    _assert_mock_mode(r)
    shapes.Audit.model_validate(r.json())


def test_whatif_rejects_bad_block(client):
    r = client.post("/whatif", json={"clinic": "c", "shift": {"block": "monday-8", "to": 10}})
    assert r.status_code == 422


# ---- POST /plan ------------------------------------------------------------ #
def test_plan_matches_contract(client, maria_request):
    r = client.post("/plan", json=maria_request)
    assert r.status_code == 200
    _assert_mock_mode(r)
    shapes.Plan.model_validate(r.json())


def test_maria_gets_escort_aware_plan(client, maria_request):
    """Done-by-H6: positive-FIT colonoscopy, works 7-15, Spanish, no escort."""
    body = client.post("/plan", json=maria_request).json()
    kinds = [o["kind"] for o in body["options"]]

    assert "slot" not in kinds  # escort required: never transit-only
    assert kinds[0] == "ride"
    ride = body["options"][0]
    assert ride["details"]["escort_required"] is True
    assert ride["details"]["has_escort"] is False
    assert ride["details"]["slot"] == "2026-11-12T15:30:00"  # the 08:00 slot is inside her shift
    assert "prep" in kinds
    prep = next(o for o in body["options"] if o["kind"] == "prep")
    assert prep["details"]["language"] == "es"
    assert body["pt1_prefill"]["mock_appointment_time"] == "15:30"
    assert body["pt1_prefill"]["mock_provider_attestation"] is None


def test_plan_unknown_visit_type(client, maria_request):
    r = client.post("/plan", json={**maria_request, "visit_type": "not-a-type"})
    assert r.status_code == 422


def test_plan_rejects_extra_fields(client, maria_request):
    bad = {**maria_request, "patient": {**maria_request["patient"], "ssn": "x"}}
    assert client.post("/plan", json=bad).status_code == 422


def test_plan_rejects_bad_geoid(client, maria_request):
    bad = {**maria_request, "patient": {**maria_request["patient"], "origin_bg": "25013"}}
    assert client.post("/plan", json=bad).status_code == 422


# ---- GET /provenance ------------------------------------------------------- #
def test_provenance_matches_contract(client):
    r = client.get("/provenance", params={"id": "mock-audit-cell"})
    assert r.status_code == 200
    _assert_mock_mode(r)
    body = shapes.Provenance.model_validate(r.json())
    assert "MOCK" in body.source.name


def test_provenance_unknown_id(client):
    assert client.get("/provenance", params={"id": "nope"}).status_code == 404


def test_provenance_requires_id(client):
    assert client.get("/provenance").status_code == 422


# ---- real mode: never falls back to mocks ---------------------------------- #
def test_real_mode_reports_unavailable(monkeypatch, maria_request):
    from fastapi.testclient import TestClient

    from api import deps
    from api.main import create_app
    from engine import audit as engine_audit

    monkeypatch.setenv("SLOT_TO_STOP_DATA", "real")
    # Simulate "cube not built yet" regardless of what is cached on this machine.
    monkeypatch.setattr(engine_audit, "CUBE_PATH", engine_audit.ROOT / "does-not-exist.parquet")
    deps._load_cube_origins.cache_clear()
    real = TestClient(create_app())
    assert real.get("/health").json()["data_mode"] == "real"
    assert real.get("/audit", params={"clinic": "c", "community": "h", "day": "mon"}).status_code == 503
    assert real.get("/provenance", params={"id": "mock-audit-cell"}).status_code == 503
    assert real.post("/plan", json=maria_request).status_code == 503
