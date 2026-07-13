#!/usr/bin/env python3
"""Build an inventory for 2DGS experiment output folders."""

from __future__ import annotations

import argparse
import ast
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TRAIN_METRIC_RE = re.compile(
    r"\[ITER (?P<iter>\d+)\] Evaluating train: L1 (?P<l1>[0-9.eE+-]+) PSNR (?P<psnr>[0-9.eE+-]+)"
)
POINTS_RE = re.compile(r"Points=(?P<points>\d+)")
INIT_POINTS_RE = re.compile(r"Number of points at initialisation\s*:\s*(?P<points>\d+)")


@dataclass
class RunInfo:
    name: str
    source_path: str = ""
    model_path: str = ""
    resolution: str = ""
    image_dir: str = ""
    has_cfg: bool = False
    has_train_log: bool = False
    has_render_log: bool = False
    has_train_renders: bool = False
    has_traj: bool = False
    has_mesh: bool = False
    file_count: int = 0
    size_gb: float = 0.0
    initial_points: str = ""
    final_iter: str = ""
    final_l1: str = ""
    final_psnr: str = ""
    final_points_log: str = ""
    final_ply_vertices: str = ""
    final_ply_mb: str = ""
    iterations: str = ""
    notes: str = ""


def parse_namespace(text: str) -> dict[str, object]:
    """Parse a repr like Namespace(a=1, b='x') into a dict."""
    text = text.strip()
    if not text.startswith("Namespace(") or not text.endswith(")"):
        return {}

    inner = text[len("Namespace(") : -1]
    result: dict[str, object] = {}
    for match in re.finditer(r"(\w+)=", inner):
        key = match.group(1)
        start = match.end()
        next_match = re.search(r",\s*\w+=", inner[start:])
        end = start + next_match.start() if next_match else len(inner)
        raw_value = inner[start:end].rstrip(", ")
        try:
            result[key] = ast.literal_eval(raw_value)
        except (ValueError, SyntaxError):
            result[key] = raw_value
    return result


def count_files_and_size(path: Path) -> tuple[int, int]:
    total_size = 0
    count = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            count += 1
            try:
                total_size += file_path.stat().st_size
            except OSError:
                pass
    return count, total_size


def newest_iteration_ply(run_dir: Path) -> Path | None:
    candidates = []
    for ply in (run_dir / "point_cloud").glob("iteration_*/point_cloud.ply"):
        match = re.search(r"iteration_(\d+)", str(ply))
        if match:
            candidates.append((int(match.group(1)), ply))
    if not candidates:
        return None
    return sorted(candidates)[-1][1]


def ply_vertex_count(path: Path) -> str:
    try:
        with path.open("r", encoding="ascii", errors="ignore") as handle:
            for line in handle:
                if line.startswith("element vertex "):
                    return line.split()[-1].strip()
                if line.strip() == "end_header":
                    break
    except OSError:
        return ""
    return ""


def parse_train_log(path: Path, info: RunInfo) -> None:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return

    for line in lines:
        init = INIT_POINTS_RE.search(line)
        if init:
            info.initial_points = init.group("points")

        points = POINTS_RE.search(line)
        if points:
            info.final_points_log = points.group("points")

        metric = TRAIN_METRIC_RE.search(line)
        if metric:
            info.final_iter = metric.group("iter")
            info.final_l1 = metric.group("l1")
            info.final_psnr = metric.group("psnr")

    info.iterations = info.final_iter


def inspect_run(run_dir: Path) -> RunInfo:
    info = RunInfo(name=run_dir.name)
    info.file_count, total_size = count_files_and_size(run_dir)
    info.size_gb = round(total_size / (1024**3), 3)

    cfg_path = run_dir / "cfg_args"
    info.has_cfg = cfg_path.exists()
    if cfg_path.exists():
        parsed = parse_namespace(cfg_path.read_text(encoding="utf-8", errors="ignore"))
        info.source_path = str(parsed.get("source_path", ""))
        info.model_path = str(parsed.get("model_path", ""))
        info.resolution = str(parsed.get("resolution", ""))
        info.image_dir = str(parsed.get("images", ""))

    train_log = run_dir / "train.log"
    info.has_train_log = train_log.exists()
    if train_log.exists():
        parse_train_log(train_log, info)

    render_log = run_dir / "render.log"
    info.has_render_log = render_log.exists() and render_log.stat().st_size > 0
    info.has_train_renders = (run_dir / "train").exists()
    info.has_traj = (run_dir / "traj").exists()
    info.has_mesh = any(run_dir.glob("**/fuse*.ply")) or any(run_dir.glob("**/mesh*.ply"))

    final_ply = newest_iteration_ply(run_dir)
    if final_ply:
        info.final_ply_vertices = ply_vertex_count(final_ply)
        info.final_ply_mb = f"{final_ply.stat().st_size / (1024**2):.1f}"
        match = re.search(r"iteration_(\d+)", str(final_ply))
        if not info.final_iter and match:
            info.final_iter = match.group(1)
            info.iterations = match.group(1)

    if not info.has_train_log:
        info.notes = "missing train.log"
    if not info.has_render_log and info.has_train_renders:
        info.notes = (info.notes + "; " if info.notes else "") + "render log missing/empty"
    return info


def iter_runs(root: Path) -> Iterable[RunInfo]:
    for child in sorted(root.iterdir()):
        if child.is_dir():
            yield inspect_run(child)


def write_csv(path: Path, rows: list[RunInfo]) -> None:
    fields = list(RunInfo.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def write_markdown(path: Path, root: Path, rows: list[RunInfo]) -> None:
    lines = [
        "# 2DGS Output Index",
        "",
        f"Output root: `{root}`",
        "",
        "This file is generated by `scripts/output_inventory.py`. Add qualitative notes in `RUN_NOTES.md` so this index can be safely regenerated.",
        "",
        "## Current Runs",
        "",
        "| Run | Dataset | Iter | L1 | PSNR | Points | Size GB | Renders | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]

    for row in rows:
        dataset = Path(row.source_path).name if row.source_path else ""
        renders = []
        if row.has_train_renders:
            renders.append("train")
        if row.has_traj:
            renders.append("traj")
        if row.has_mesh:
            renders.append("mesh")
        render_text = ", ".join(renders) if renders else ""
        points = row.final_ply_vertices or row.final_points_log
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row.name}`",
                    f"`{dataset}`",
                    row.final_iter,
                    row.final_l1,
                    row.final_psnr,
                    points,
                    f"{row.size_gb:.3f}",
                    render_text,
                    row.notes,
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Recommended Run Naming",
            "",
            "`<scene>_<capture-or-dataset>_<fov-or-preprocess>_<train-purpose>_<iterations>_<version>`",
            "",
            "Examples:",
            "",
            "- `reception_hall_geoscanS2_v2_scale1_baseline_30k_v1`",
            "- `reception_hall_geoscanS2_v2_narrow_text_30k_v1`",
            "- `reception_hall_geoscanS2_v2_scale1_detail_60k_v1`",
            "",
            "## What To Keep",
            "",
            "- Keep: `cfg_args`, `train.log`, useful `render.log`, final `point_cloud/iteration_*/point_cloud.ply`, curated comparison images, and qualitative notes.",
            "- Optional archive: TensorBoard `events.out.tfevents.*`, intermediate `iteration_7000` point clouds, and full train-view render folders once comparison crops have been saved.",
            "- Do not delete a run before its dataset path, command, final metrics, and visual conclusion are recorded.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path, help="Directory containing 2DGS run output folders.")
    parser.add_argument("--markdown", type=Path, default=None, help="Markdown index path.")
    parser.add_argument("--csv", type=Path, default=None, help="CSV index path.")
    args = parser.parse_args()

    root = args.output_root.resolve()
    rows = list(iter_runs(root))

    markdown_path = args.markdown or root / "RUN_INDEX.md"
    csv_path = args.csv or root / "RUN_INDEX.csv"
    write_markdown(markdown_path, root, rows)
    write_csv(csv_path, rows)

    print(f"Indexed {len(rows)} runs")
    print(f"Wrote {markdown_path}")
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
