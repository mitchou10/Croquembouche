"""The version of the application: the one of the installed package, which the release bumps (pyproject.toml)."""

from importlib.metadata import PackageNotFoundError, version

# What is said when the package is not installed (running from the sources, with no metadata to read).
UNKNOWN = "inconnue"


def app_version() -> str:
    try:
        return version("croquembouche-backend")
    except PackageNotFoundError:
        return UNKNOWN
