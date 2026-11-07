import asyncio
import subprocess
import sys
from pathlib import Path

from curl_cffi.requests import AsyncSession
from dtek_client import DtekClient
from dtek_client.browser_auth import get_cleared_cookies
from dtek_client.exceptions import DtekDataError
from iterfzf import iterfzf
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .schedule import format_interval, get_outage_intervals

BASE_URL = "https://www.dtek-kem.com.ua"
SCHEDULE_URL = f"{BASE_URL}/ua/shutdowns"
CITY = "м. Київ"
console = Console()
err_console = Console(stderr=True)


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


def print_schedule(response, street: str, number: str) -> None:
    house = response.houses.get(number)

    if not house:
        err_console.print("⚠️ [bold red]Адресу не знайдено[/]")
        return

    if house.is_excluded:
        err_console.print("⚠️ [bold yellow]Цієї адреси немає в графіках[/]")
        return

    if response.fact is None:
        err_console.print("📡 [bold yellow]Графік наразі недоступний[/]")
        return

    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Група", style="bold magenta", justify="center")
    table.add_column("Графік на сьогодні", justify="left")

    for group_id in house.group_ids:
        schedule = response.fact.get_group_today(group_id)

        if schedule is None:
            table.add_row(group_id, "[dim italic]Інформація відсутня[/]")
            continue

        intervals = get_outage_intervals(schedule)

        if intervals:
            text = "\n".join(
                f"[bold red]🔴 {format_interval(s, e)}[/]" for s, e in intervals
            )
        else:
            text = "[bold green]🟢 Відключень не очікується[/]"

        table.add_row(group_id, text)
    title = f"📍 [bold white]{street}, {number}[/]"
    console.print(Panel(table, title=title, border_style="cyan", expand=False))


def spin(text: str):
    return console.status(f"[bold green]{text}[/bold green]", spinner="bouncingBall")


async def main() -> None:
    with spin("Відкриваю сесію..."):
        session = await make_session()
    async with DtekClient(
        "kem", ajax_url=f"{BASE_URL}/ua/ajax", session=session
    ) as client:
        with spin("Завантажую вулиці..."):
            streets = await client.get_streets(CITY)
        street = pick([s.name for s in streets], "Вулиця> ")
        with spin("Завантажую будинки..."):
            response = await client.get_home_num(city=CITY, street=street)
        number = pick(list(response.houses), "Будинок> ")

        print_schedule(response, street, number)


def ensure_chromium() -> None:
    """Download Chromium for Playwright if it is not already installed."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if Path(p.chromium.executable_path).exists():
            return

    err_console.print("[cyan]Завантажую Chromium (лише один раз)...[/cyan]")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=sys.stderr,  # keep stdout clean for MCP
        )
    except subprocess.CalledProcessError:
        err_console.print(
            "[bold red]Не вдалося завантажити Chromium.[/bold red] "
            "Спробуйте вручну: python -m playwright install chromium"
        )
        sys.exit(1)


def run() -> None:
    ensure_chromium()
    try:
        asyncio.run(main())
    except DtekDataError as e:
        err_console.print(f"[bold red]Помилка DTEK:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
