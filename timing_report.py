"""Compare DEM log timings using only the Python standard library."""

import math
import re
from pathlib import Path


DEFAULT_PATTERN = (
    r"^\s*(?P<seconds>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    r"\s+seconds\s+\(wall time\)\s+to finish the simulation\b"
)


def _compile(pattern):
    compiled = re.compile(pattern)
    if "seconds" not in compiled.groupindex:
        raise ValueError("Timing pattern must contain a named group: (?P<seconds>...)")
    return compiled


def _read_seconds(path, pattern):
    """Use the last matching line, including for logs with appended runs."""
    value = None
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = pattern.search(line)
            if match:
                value = float(match.group("seconds"))
    if value is None:
        raise ValueError("no matching timing line")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("timing must be finite and greater than zero")
    return value


def generate_timing_report(config, base_dir, output_dir):
    """Write a Markdown report; missing/unusable demo logs are nonfatal skips."""
    if not config.get("enabled", True):
        return None

    def resolve(value):
        return (Path(base_dir) / value).resolve()

    known_dir = resolve(config.get("known_dir", "known_timing"))
    new_dir = resolve(config.get("new_dir", "results"))
    report_path = resolve(config["output"]) if "output" in config else Path(output_dir) / "timing_report.md"
    pattern = _compile(config.get("pattern", DEFAULT_PATTERN))
    overrides = {
        name: _compile(value) for name, value in config.get("patterns", {}).items()
    }
    file_glob = config.get("file_glob", "DEMdemo_*")
    known_files = {p.name: p for p in known_dir.glob(file_glob) if p.is_file()}
    new_files = {p.name: p for p in new_dir.glob(file_glob) if p.is_file()}
    rows = []
    skipped = []
    for name in sorted(known_files.keys() | new_files.keys()):
        if name not in known_files or name not in new_files:
            missing = "known" if name not in known_files else "new"
            skipped.append((name, f"missing {missing} log"))
            continue
        extraction = overrides.get(name, pattern)
        try:
            known = _read_seconds(known_files[name], extraction)
            new = _read_seconds(new_files[name], extraction)
        except (OSError, ValueError, TypeError) as exc:
            skipped.append((name, str(exc)))
            continue
        change = (new / known - 1) * 100
        status = "faster" if new < known else "slower" if new > known else "unchanged"
        rows.append((name, known, new, change, status))

    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")

    lines = [
        "# Simulation timing comparison", "",
        f"Known logs: {known_dir}", "", f"New logs: {new_dir}", "",
        "Change = (new / known - 1) × 100%. Negative means faster; positive means slower.",
        "", f"Compared: {len(rows)}. Skipped: {len(skipped)}.", "",
        "| Demo log | Known (s) | New (s) | Change | Result |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for name, known, new, change, status in rows:
        lines.append(f"| {escape(name)} | {known:.9g} | {new:.9g} | {change:+.2f}% | {status} |")
    if not rows:
        lines.extend(["", "No comparable timing data found."])
    if skipped:
        lines.extend(["", "## Skipped logs", ""])
        lines.extend(f"- {escape(name)}: {escape(reason)}" for name, reason in skipped)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Timing report: {report_path} ({len(rows)} compared, {len(skipped)} skipped)")
    return report_path
