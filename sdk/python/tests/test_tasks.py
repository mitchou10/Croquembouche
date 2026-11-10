import pytest

from croquembouche import NotFoundError


def task(name="template_matching.classify_pages", version="1.25.0", online=1):
    return {
        "name": name,
        "version": version,
        "description": "What each page is",
        "author": "Croquembouche",
        "inputSchema": {"type": "object", "properties": {"template_ids": {"type": "array"}}},
        "parameters": {"type": "object", "properties": {"threshold": {"type": "number", "default": 0.8}}},
        "outputSchema": {"type": "array"},
        "createdAt": "2026-11-10T10:00:00Z",
        "online": online,
        "instances": [
            {
                "instanceId": "template_matching-host-ab12",
                "service": "template_matching",
                "hostname": "host",
                "startedAt": "2026-11-10T10:00:00Z",
                "lastSeenAt": "2026-11-10T10:01:00Z",
                "online": bool(online),
            }
        ],
    }


async def test_the_tasks_of_the_workers_are_listed_with_their_schemas(api, client):
    api.on("GET /api/tasks", [task(), task("ocr.read_document", "1.25.0", 0)])

    listed = await client.tasks.list(online=True)

    assert api.seen[-1].url.params["online"] == "true"
    first, second = listed
    assert (first.name, first.version, first.online, first.author) == (
        "template_matching.classify_pages",
        "1.25.0",
        1,
        "Croquembouche",
    )
    assert first.input_schema.to_dict() == {"type": "object", "properties": {"template_ids": {"type": "array"}}}
    assert first.parameters.to_dict()["properties"]["threshold"]["default"] == 0.8
    assert first.output_schema.to_dict() == {"type": "array"}
    assert first.instances[0].instance_id == "template_matching-host-ab12" and first.instances[0].online is True
    assert second.online == 0 and second.instances[0].online is False


async def test_the_versions_of_a_task(api, client):
    api.on("GET /api/tasks/template_matching.classify_pages", [task(version="1.24.0"), task(version="1.25.0")])
    api.on("GET /api/tasks/unknown", {"detail": "Not found"}, 404)

    versions = await client.tasks.get("template_matching.classify_pages")

    assert [t.version for t in versions] == ["1.24.0", "1.25.0"]
    assert api.seen[-1].url.params["online"] == "false"
    with pytest.raises(NotFoundError):
        await client.tasks.get("unknown")
