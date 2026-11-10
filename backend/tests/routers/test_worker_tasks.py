"""The tasks the workers declare: registered when an instance starts, kept alive by its heartbeat."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.worker import KEY

INSTANCE = "template_matching-host-1-ab12"


def task(name="template_matching.classify_pages", version="1.25.0", **changes):
    return {
        "name": name,
        "version": version,
        "description": "What each page is",
        "author": "Croquembouche",
        "inputSchema": {"type": "object", "properties": {"pageKeys": {"type": "array"}}},
        "parameters": {"type": "object", "properties": {"threshold": {"type": "number", "default": 0.8}}},
        "outputSchema": {"type": "array"},
    } | changes


async def register(client, instance=INSTANCE, tasks=None, **changes):
    body = {"service": "template_matching", "hostname": "host", "tasks": [task()] if tasks is None else tasks}
    return await client.put(f"/internal/workers/{instance}", json=body | changes, headers=KEY)


@pytest.fixture
def alice(as_user):
    as_user("alice", name="Alice")


async def test_an_instance_registers_its_tasks_and_they_are_on_offer(db_client, alice):
    assert (await register(db_client)).status_code == 204

    [listed] = (await db_client.get("/api/tasks")).json()

    assert (listed["name"], listed["version"], listed["author"]) == (
        "template_matching.classify_pages",
        "1.25.0",
        "Croquembouche",
    )
    assert listed["inputSchema"]["properties"] == {"pageKeys": {"type": "array"}}
    assert listed["parameters"]["properties"]["threshold"]["default"] == 0.8
    assert listed["outputSchema"] == {"type": "array"}
    assert listed["online"] == 1 and listed["instances"][0]["instanceId"] == INSTANCE
    assert listed["instances"][0]["service"] == "template_matching" and listed["instances"][0]["online"] is True


async def test_the_workers_key_is_asked_for(db_client, alice):
    for call in (
        db_client.put(f"/internal/workers/{INSTANCE}", json={"tasks": []}),
        db_client.post(f"/internal/workers/{INSTANCE}/heartbeat"),
        db_client.delete(f"/internal/workers/{INSTANCE}"),
    ):
        assert (await call).status_code in (401, 503)
    assert (
        await db_client.put(f"/internal/workers/{INSTANCE}", json={"tasks": []}, headers={"X-Internal-Key": "x"})
    ).status_code == 401


async def test_the_same_task_of_two_instances_is_one_task_with_two_instances(db_client, alice):
    await register(db_client, "i1")
    await register(db_client, "i2")
    await register(db_client, "i3", tasks=[task(version="1.26.0")])

    listed = (await db_client.get("/api/tasks")).json()

    assert [(t["version"], t["online"], len(t["instances"])) for t in listed] == [("1.25.0", 2, 2), ("1.26.0", 1, 1)]
    assert {i["instanceId"] for i in listed[0]["instances"]} == {"i1", "i2"}


async def test_versions_are_in_order_as_numbers(db_client, alice):
    await register(db_client, tasks=[task(version="1.10.0"), task(version="1.9.0"), task("a.first", "2.0.0")])

    listed = (await db_client.get("/api/tasks")).json()

    assert [(t["name"], t["version"]) for t in listed] == [
        ("a.first", "2.0.0"),
        ("template_matching.classify_pages", "1.9.0"),
        ("template_matching.classify_pages", "1.10.0"),
    ]


async def test_registering_again_replaces_what_the_instance_declared(db_client, alice):
    await register(db_client, tasks=[task(), task("template_matching.ping", description="Pong")])
    await register(db_client, tasks=[task(description="Changed")])

    listed = (await db_client.get("/api/tasks")).json()

    assert [(t["name"], t["description"]) for t in listed] == [("template_matching.classify_pages", "Changed")]


async def test_a_task_declared_twice_in_one_registration_is_kept_once(db_client, alice):
    assert (await register(db_client, tasks=[task(description="first"), task(description="second")])).status_code == 204

    [listed] = (await db_client.get("/api/tasks")).json()
    assert listed["description"] == "second"


async def test_an_instance_that_is_silent_is_offline_and_its_tasks_are_not_on_offer(db_client, alice, db):
    await register(db_client)
    await db.execute(
        text("update worker_heartbeats set last_seen_at = now() - interval '5 minutes' where instance_id = :i"),
        {"i": INSTANCE},
    )

    [listed] = (await db_client.get("/api/tasks")).json()
    assert listed["online"] == 0 and listed["instances"][0]["online"] is False
    assert (await db_client.get("/api/tasks?online=true")).json() == []

    # It says it is alive again.
    assert (await db_client.post(f"/internal/workers/{INSTANCE}/heartbeat", headers=KEY)).status_code == 204
    assert (await db_client.get("/api/tasks?online=true")).json()[0]["online"] == 1


async def test_the_heartbeat_of_an_instance_that_is_not_known_is_refused_so_that_it_registers_again(db_client, alice):
    assert (await db_client.post("/internal/workers/nobody/heartbeat", headers=KEY)).status_code == 404


async def test_an_instance_that_stops_takes_its_tasks_off_offer(db_client, alice):
    await register(db_client, "i1")
    await register(db_client, "i2")

    assert (await db_client.delete("/internal/workers/i1", headers=KEY)).status_code == 204
    assert (await db_client.delete("/internal/workers/i1", headers=KEY)).status_code == 204  # and again: nothing to do

    [listed] = (await db_client.get("/api/tasks")).json()
    assert [i["instanceId"] for i in listed["instances"]] == ["i2"]


async def test_instances_silent_for_days_are_forgotten_when_another_registers(db_client, alice, db):
    await register(db_client, "old")
    await db.execute(
        text("update worker_heartbeats set last_seen_at = now() - interval '8 days' where instance_id = 'old'")
    )

    await register(db_client, "new")

    [listed] = (await db_client.get("/api/tasks")).json()
    assert [i["instanceId"] for i in listed["instances"]] == ["new"]
    assert (await db.execute(text("select count(*) from worker_tasks"))).scalar() == 1


async def test_a_task_is_read_by_name_with_all_its_versions(db_client, alice):
    await register(db_client, tasks=[task(version="1.0.0"), task(version="2.0.0"), task("other", "1.0.0")])

    versions = (await db_client.get("/api/tasks/template_matching.classify_pages")).json()

    assert [t["version"] for t in versions] == ["1.0.0", "2.0.0"]
    assert (await db_client.get("/api/tasks/unknown")).status_code == 404


async def test_the_tasks_are_for_whoever_is_signed_in(db_client, as_user):
    as_user("service-account-mille-feuille", roles=["catalogue-reader"], service="mille-feuille")
    await register(db_client)

    assert len((await db_client.get("/api/tasks")).json()) == 1


async def test_a_registration_is_limited(db_client, alice):
    many = [task(version=f"1.0.{n}") for n in range(101)]
    assert (await register(db_client, tasks=many)).status_code == 422
    assert (await register(db_client, tasks=[task(name="")])).status_code == 422


def test_the_delay_to_be_offline_is_a_setting():
    from app.config import MatchingSettings

    assert MatchingSettings().WORKER_HEARTBEAT_TTL_SECONDS == 90 and timedelta(
        days=MatchingSettings().WORKER_PURGE_DAYS
    )
