import tomllib
from pathlib import Path

from app import version


async def test_the_api_says_the_version_of_the_release(client):
    response = await client.get("/api/version")

    assert response.status_code == 200
    # The one the release bumps in pyproject.toml, which is the package that is installed.
    pyproject = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())
    assert response.json() == {"version": pyproject["project"]["version"]}


async def test_it_needs_no_one_to_be_signed_in(client):
    assert (await client.get("/api/version")).status_code == 200


def test_a_package_that_is_not_installed_has_no_version_to_say(monkeypatch):
    def missing(name):
        raise version.PackageNotFoundError(name)

    monkeypatch.setattr(version, "version", missing)

    assert version.app_version() == version.UNKNOWN
