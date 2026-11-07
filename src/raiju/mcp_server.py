from dtek_client import DtekClient
from mcp.server.mcpserver import MCPServer

from .cli import BASE_URL, CITY, make_session
from .schedule import format_interval, get_outage_intervals

mcp = MCPServer("raiju")


@mcp.tool()
async def find_streets(query: str) -> list[str]:
    """Find Kyiv streets whose name contains the given text (e.g. 'Хрещатик')."""
    session = await make_session()
    async with DtekClient(
        "kem", ajax_url=f"{BASE_URL}/ua/ajax", session=session
    ) as client:
        streets = await client.get_streets(CITY)
    q = query.lower()
    return [s.name for s in streets if q in s.name.lower()][:20]


@mcp.tool()
async def get_outages(street: str, house: str) -> str:
    """Get today's DTEK power outage schedule for an address in Kyiv.

    street: exact street name as returned by find_streets.
    house: house number, e.g. '37'.
    """
    session = await make_session()
    async with DtekClient(
        "kem", ajax_url=f"{BASE_URL}/ua/ajax", session=session
    ) as client:
        response = await client.get_home_num(city=CITY, street=street)

    if house not in response.houses:
        return f"Будинок {house} не знайдено на {street}"
    h = response.houses[house]
    if h.is_excluded:
        return "Ця адреса не входить до графіка"
    if response.fact is None:
        return "Графік зараз недоступний"

    lines = []
    for group_id in h.group_ids:
        schedule = response.fact.get_group_today(group_id)
        if schedule is None:
            lines.append(f"{group_id}: графік відсутній")
            continue
        intervals = get_outage_intervals(schedule)
        if intervals:
            times = ", ".join(format_interval(s, e) for s, e in intervals)
            lines.append(f"{group_id}: відключення {times}")
        else:
            lines.append(f"{group_id}: відключень не очікується")
    return "\n".join(lines)


def main() -> None:
    from .cli import ensure_chromium

    ensure_chromium()
    mcp.run()  # stdio transport; never print() to stdout here
