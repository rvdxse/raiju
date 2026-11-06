HALVES = {
    "yes": (False, False),
    "no": (True, True),
    "first": (True, False),
    "second": (False, True),
}


def get_outage_intervals(schedule: dict) -> list[tuple[int, int]]:
    """Повертає інтервали відключень у хвилинах від початку доби."""
    cells: list[bool] = []
    for _, status in sorted(schedule.items(), key=lambda x: int(x[0])):
        cells.extend(HALVES.get(str(status).lower(), (False, False)))

    intervals = []
    start = None
    for i, off in enumerate(cells):
        if off and start is None:
            start = i
        elif not off and start is not None:
            intervals.append((start * 30, i * 30))
            start = None
    if start is not None:
        intervals.append((start * 30, len(cells) * 30))
    return intervals


def format_interval(start: int, end: int) -> str:
    return f"{start // 60:02d}:{start % 60:02d}–{end // 60:02d}:{end % 60:02d}"
