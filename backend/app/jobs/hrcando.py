"""Job postings from career pages built on hrcando (career.hrcando.ir/co/<company>/… and
company domains such as jobs.bitpin.org). They all share one public API keyed by the job's UUID.
"""

import re

import httpx

from app.config import Settings
from app.jobs.base import JobFetchError, JobPosting
from app.jobs.html import html_to_text

API_URL = "https://careerapi.hrcando.ir/api/v1/CareerPage/GetCareerPageJobPageInfoByJobGuid"
_JOB_PATH = re.compile(r"/job-detail/([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})")
TIMEOUT_SECONDS = 10.0


def _name(value: object) -> str | None:
    return value.get("name") if isinstance(value, dict) else None


class HrcandoAdapter:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client

    def can_handle(self, url: str) -> bool:
        return self.can_handle_url(url)

    @staticmethod
    def can_handle_url(url: str) -> bool:
        return _JOB_PATH.search(url) is not None

    async def fetch(self, url: str) -> JobPosting:
        match = _JOB_PATH.search(url)
        if not match:
            raise JobFetchError(f"not an hrcando job link: {url}")
        headers = {
            "accept": "application/json, text/plain, */*",
            "careerauthkey": self._settings.hrcando_career_auth_key,
            "address": url,
            "origin": "https://career.hrcando.ir",
            "referer": "https://career.hrcando.ir/",
        }
        endpoint = f"{API_URL}/{match.group(1).lower()}"
        try:
            if self._client is not None:
                response = await self._client.get(endpoint, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                    response = await client.get(endpoint, headers=headers)
        except httpx.HTTPError as exc:
            raise JobFetchError(f"hrcando is unreachable: {exc}") from exc

        payload = response.json() if response.status_code == 200 else {}
        data = payload.get("data") if payload.get("succeed") is True else None
        if not isinstance(data, dict):
            raise JobFetchError(
                f"Couldn't load that job from hrcando (HTTP {response.status_code}); "
                "the posting may have closed"
            )

        company = data.get("companyInfo") or {}
        return JobPosting(
            source="hrcando",
            url=url,
            company=company.get("companyName"),
            title=data.get("title"),
            seniority=_name(data.get("seniorityLevel")),
            location=_name(data.get("city")),
            employment_type=_name(data.get("workType")),
            remote=data.get("isRemote"),
            experience_years=data.get("requiredExperienceYear"),
            description_text=html_to_text(data.get("description") or ""),
            raw=data,
        )


if __name__ == "__main__":
    import asyncio
    import sys

    from app.config import get_settings

    posting = asyncio.run(HrcandoAdapter(get_settings()).fetch(sys.argv[1]))
    print(posting.model_dump_json(indent=2, exclude={"raw"}))
