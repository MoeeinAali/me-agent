import json
from pathlib import Path

import httpx
import pytest
import respx

from app.config import get_settings
from app.jobs.base import JobFetchError, UnsupportedJobUrl, resolve_job
from app.jobs.hrcando import API_URL, HrcandoAdapter
from app.jobs.html import html_to_text

FIXTURE = json.loads((Path(__file__).parents[1] / "fixtures" / "hrcando_milli.json").read_text())
MILLI = "https://career.hrcando.ir/co/Milli/job-detail/6867af3e-e373-4659-85a8-a9420cd14388"
BITPIN = "https://jobs.bitpin.org/job-detail/076fb0c1-c10d-4b07-8137-dc858d82b7cc"


def test_can_handle_custom_domain() -> None:
    adapter = HrcandoAdapter(get_settings())
    assert adapter.can_handle(MILLI)
    assert adapter.can_handle(BITPIN)
    assert not adapter.can_handle("https://jobinja.ir/companies/x/jobs/AbC1/senior")
    assert not adapter.can_handle("https://career.hrcando.ir/co/Milli")


def test_html_to_text_keeps_structure() -> None:
    text = html_to_text("<p>Hi&zwnj;there</p><h3>Must</h3><ul><li><p>Go</p></li><li>K8s</li></ul>")
    assert text == "Hi‌there\n\n## Must\n- Go\n- K8s"


@respx.mock
async def test_fetch_maps_milli_fixture() -> None:
    route = respx.get(f"{API_URL}/6867af3e-e373-4659-85a8-a9420cd14388").mock(
        return_value=httpx.Response(200, json=FIXTURE)
    )
    posting = await HrcandoAdapter(get_settings()).fetch(MILLI)

    assert posting.source == "hrcando"
    assert posting.title == "کارشناس پشتیبانی و امور مشتریان (شیفت شب حضوری)"
    assert posting.company == "میلی‌"
    assert posting.experience_years == 1
    assert posting.remote is False
    assert posting.seniority == "کارشناس"
    assert posting.location == "تهران"
    assert posting.employment_type == "تمام وقت"
    assert "## شرایط احراز" in posting.description_text
    assert "- حداقل ۱ سال تجربه در پشتیبانی یا خدمات مشتریان" in posting.description_text

    headers = route.calls[0].request.headers
    assert headers["careerauthkey"] == get_settings().hrcando_career_auth_key
    assert headers["address"] == MILLI
    assert headers["origin"] == "https://career.hrcando.ir"


@respx.mock
async def test_fetch_500_raises_jobfetcherror() -> None:
    respx.get(url__startswith=API_URL).mock(return_value=httpx.Response(500))
    with pytest.raises(JobFetchError, match="may have closed"):
        await HrcandoAdapter(get_settings()).fetch(MILLI)


@respx.mock
async def test_fetch_unsucceeded_payload_raises() -> None:
    respx.get(url__startswith=API_URL).mock(
        return_value=httpx.Response(200, json={"data": None, "succeed": False})
    )
    with pytest.raises(JobFetchError):
        await HrcandoAdapter(get_settings()).fetch(MILLI)


async def test_unknown_url_message() -> None:
    with pytest.raises(UnsupportedJobUrl, match="paste the job description"):
        await resolve_job(url="https://jobinja.ir/x", text=None, pdf=None)
