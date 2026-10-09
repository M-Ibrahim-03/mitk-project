import asyncio
from importlib.metadata import version
from pathlib import Path

import httpx
from packaging.requirements import Requirement

from veil.api import app


def test_google_genai_installed_version_matches_declared_requirement() -> None:
    requirements_file = Path(__file__).resolve().parents[1] / "requirements.txt"
    requirement = next(
        Requirement(line.strip())
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("google-genai")
    )

    assert version("google-genai") in requirement.specifier


def test_health_endpoint() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "veil"}
