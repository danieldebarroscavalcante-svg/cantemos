from datetime import datetime

import pytest

from app.modules.events.models import Event, EventSession
from app.modules.events.schemas import EventSettingsIn
from app.modules.events.service import update_settings
from app.modules.organizations.models import Role
from app.modules.tickets.models import TicketKind, TicketType
from tests.conftest import auth_headers, make_member

URL = "/api/v1/org/events/cantemos-2026/settings"

BASE = {
    "starts_at": "2026-11-19T18:30:00",
    "doors_open_at": "2026-11-19T18:00:00",
    "capacity": 120,
    "overbooking_percent": 20,
    "max_tickets_per_order": 5,
    "priority_quota": 10,
    "reserved_quotas": [],
}


@pytest.fixture
def event(db, org):
    ev = Event(organization_id=org.id, slug="cantemos-2026", title="CANTEMOS 2026")
    db.add(ev)
    db.flush()
    db.add(
        EventSession(event_id=ev.id, name="Quinta", starts_at=datetime(2026, 11, 19), capacity=1)
    )
    db.flush()
    update_settings(db, ev, EventSettingsIn(**BASE))
    return ev


def put(client, headers, **changes):
    return client.put(URL, json={**BASE, **changes}, headers=headers)


def test_defaults_give_144_registrations(client, admin, event):
    body = client.get(URL, headers=auth_headers(client)).json()
    assert body["registration_limit"] == 144
    assert body["general"]["quantity"] == 134
    assert body["priority"]["quantity"] == 10
    assert body["starts_at"] == "2026-11-19T18:30:00"


def test_times_are_stored_in_utc(db, event):
    session = db.query(EventSession).one()
    assert session.starts_at == datetime(2026, 11, 19, 21, 30)


def test_limits_can_go_up_and_down(client, admin, event):
    headers = auth_headers(client)
    body = put(client, headers, max_tickets_per_order=8, priority_quota=20).json()
    assert body["max_tickets_per_order"] == 8
    assert body["priority"]["quantity"] == 20
    assert body["general"]["quantity"] == 124

    body = put(client, headers, max_tickets_per_order=2, priority_quota=0).json()
    assert body["max_tickets_per_order"] == 2
    assert body["general"]["quantity"] == 144


def test_custom_reserved_quotas_are_created_updated_and_removed(client, admin, event):
    headers = auth_headers(client)
    body = put(
        client,
        headers,
        reserved_quotas=[
            {"name": "Família do coral", "quantity": 15},
            {"name": "Equipe e convidados", "quantity": 5},
        ],
    ).json()
    assert [q["name"] for q in body["reserved_quotas"]] == [
        "Família do coral",
        "Equipe e convidados",
    ]
    assert body["general"]["quantity"] == 144 - 10 - 20

    coral = body["reserved_quotas"][0]
    body = put(
        client, headers, reserved_quotas=[{"id": coral["id"], "name": "Coral", "quantity": 25}]
    ).json()
    assert body["reserved_quotas"] == [
        {"id": coral["id"], "name": "Coral", "quantity": 25, "issued": 0}
    ]
    assert body["general"]["quantity"] == 144 - 10 - 25


def test_overbooking_margin_changes_total(client, admin, event):
    body = put(client, auth_headers(client), overbooking_percent=50).json()
    assert body["registration_limit"] == 180
    assert body["capacity"] == 120


def test_quotas_cannot_exceed_total(client, admin, event):
    response = put(
        client,
        auth_headers(client),
        priority_quota=100,
        overbooking_percent=0,
        reserved_quotas=[{"name": "Coral", "quantity": 30}],
    )
    assert response.status_code == 422
    assert "ultrapassam" in response.json()["detail"]


def test_cannot_shrink_below_issued(db, client, admin, event):
    priority = db.query(TicketType).filter_by(kind=TicketKind.PRIORITY).one()
    priority.reserved_count = 8
    db.commit()
    response = put(client, auth_headers(client), priority_quota=5)
    assert response.status_code == 422
    assert "já emitidos" in response.json()["detail"]


def test_doors_must_open_before_start(client, admin, event):
    response = put(client, auth_headers(client), doors_open_at="2026-11-19T19:00:00")
    assert response.status_code == 422


def test_reception_cannot_view_or_edit_settings(db, client, org, event):
    make_member(db, org, "recepcao@igreja.org", Role.CHECKIN)
    headers = auth_headers(client, "recepcao@igreja.org")
    assert client.get(URL, headers=headers).status_code == 403
    assert put(client, headers).status_code == 403


def test_manager_can_view_but_not_edit(db, client, org, event):
    make_member(db, org, "producao@igreja.org", Role.MANAGER)
    headers = auth_headers(client, "producao@igreja.org")
    assert client.get(URL, headers=headers).status_code == 200
    assert put(client, headers).status_code == 403


def test_list_events(client, admin, event):
    events = client.get("/api/v1/org/events", headers=auth_headers(client)).json()
    assert events == [
        {
            "my_role": "owner",
            "slug": "cantemos-2026",
            "title": "CANTEMOS 2026",
            "status": "draft",
            "starts_at": "2026-11-19T18:30:00",
            "capacity": 120,
            "registration_limit": 144,
            "registered": 0,
        }
    ]
