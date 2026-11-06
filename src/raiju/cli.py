import asyncio
import subprocess
import sys
from pathlib import Path

from curl_cffi.requests import AsyncSession
from dtek_client import DtekClient
from dtek_client.browser_auth import get_cleared_cookies
from dtek_client.exceptions import DtekDataError
from iterfzf import iterfzf

from .schedule import format_interval, get_outage_intervals

BASE_URL = "https://www.dtek-kem.com.ua"
SCHEDULE_URL = f"{BASE_URL}/ua/shutdowns"
CITY = "м. Київ"


def pick(options: list[str], prompt: str) -> str:
    choice = iterfzf(options, prompt=prompt)
    if choice is None:  # Esc / Ctrl-C
        raise SystemExit(1)
    return choice


async def make_session() -> AsyncSession:
    cookies, csrf_token = await get_cleared_cookies(SCHEDULE_URL)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "uk,en;q=0.9",
        "Origin": BASE_URL,
        "Referer": SCHEDULE_URL,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if csrf_token:
        headers["X-CSRF-Token"] = csrf_token
    return AsyncSession(
        timeout=15.0, headers=headers, cookies=cookies, impersonate="chrome120"
    )


def print_schedule(response, number: str) -> None:
    house = response.houses[number]
    if house.is_excluded:
        print("Адреса не входить до графіка")
        return
    if response.fact is None:
        print("Графік зараз недоступний")
        return

    for group_id in house.group_ids:
        print(f"\n{group_id}")
        schedule = response.fact.get_group_today(group_id)
        if schedule is None:
            print("Графік недоступний")
            continue

        intervals = get_outage_intervals(schedule)
        if intervals:
            print("Відключення світла:")
            for start, end in intervals:
                print(f"🔴 {format_interval(start, end)}")
        else:
            print("🟢 Відключень не планується")


async def main() -> None:
    session = await make_session()
    async with DtekClient(
        "kem", ajax_url=f"{BASE_URL}/ua/ajax", session=session
    ) as client:
        streets = await client.get_streets(CITY)
        street = pick([s.name for s in streets], "Вулиця> ")

        response = await client.get_home_num(city=CITY, street=street)
        number = pick(list(response.houses), "Будинок> ")

        print_schedule(response, number)


def ensure_chromium() -> None:
    """Download Chromium for Playwright if it is not already installed."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if Path(p.chromium.executable_path).exists():
            return
    print("Завантажую Chromium (лише один раз)...", file=sys.stderr)
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
        check=True,
    )


def run() -> None:
    ensure_chromium()
    try:
        asyncio.run(main())
    except DtekDataError as e:
        sys.exit(f"Помилка DTEK: {e}")
    except KeyboardInterrupt:
        sys.exit(130)
