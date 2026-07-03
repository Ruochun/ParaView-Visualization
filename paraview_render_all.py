#!/usr/bin/env pvpython
"""
Batch-render ParaView movies/frames for multiple simulation result groups.

Run examples:
  pvpython --force-offscreen-rendering paraview_render_all.py render_jobs.example.json
  pvbatch paraview_render_all.py render_jobs.example.json

The manifest is JSON so it works with ParaView's bundled Python without extra packages.
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

from paraview.simple import *  # noqa: F401,F403 - ParaView scripts conventionally use this.


def _natural_key(path):
    """Sort file_2 before file_10."""
    text = str(path)
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def _resolve(path, base_dir):
    p = Path(path)
    if p.is_absolute():
        return str(p)
    return str((base_dir / p).resolve())


def _expand_files(spec, base_dir):
    """Return a naturally sorted list of files from a string/list manifest entry."""
    if isinstance(spec, list):
        files = [_resolve(x, base_dir) for x in spec]
    else:
        pattern = _resolve(spec, base_dir)
        if any(ch in pattern for ch in "*?["):
            files = sorted(glob.glob(pattern), key=_natural_key)
        else:
            files = [pattern]
    if not files:
        raise RuntimeError(f"No files matched: {spec}")
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        raise RuntimeError("Missing input files:\n  " + "\n  ".join(missing[:20]))
    return files


def _safe_set(proxy, name, value):
    """Set a ParaView property, but keep version-specific property failures readable."""
    if value is None:
        return
    try:
        setattr(proxy, name, value)
    except Exception as exc:  # ParaView proxy properties vary a little by version.
        print(f"WARNING: could not set {proxy}.{name} = {value!r}: {exc}", file=sys.stderr)


def _reset():
    ResetSession()


def _get_render_view():
    view = GetActiveView()
    if view is None:
        view = GetActiveViewOrCreate("RenderView")
    return view


def _get_target(job):
    """Save either active view or full layout if the state uses multiple views."""
    if job.get("save_all_views", False):
        layout = GetLayout()
        if layout is None:
            return _get_render_view()
        return layout
    return _get_render_view()


def _apply_camera_and_view(view, job, defaults, reset_default=False):
    if not hasattr(view, "ViewSize"):
        return

    resolution = job.get("resolution", defaults.get("resolution", [1920, 1080]))
    _safe_set(view, "ViewSize", resolution)

    if "background" in job:
        _safe_set(view, "Background", job["background"])

    camera = job.get("camera")
    if camera:
        mapping = {
            "position": "CameraPosition",
            "focal_point": "CameraFocalPoint",
            "view_up": "CameraViewUp",
            "parallel_scale": "CameraParallelScale",
            "view_angle": "CameraViewAngle",
        }
        for src, dst in mapping.items():
            if src in camera:
                _safe_set(view, dst, camera[src])
        if camera.get("parallel_projection") is not None:
            _safe_set(view, "CameraParallelProjection", int(bool(camera["parallel_projection"])))
    elif job.get("reset_camera", reset_default):
        ResetCamera(view)


def _animation_params(job, defaults):
    """
    Build SaveAnimation keyword arguments.

    Per-job values override defaults. For example:

      job["frame_rate"] overrides defaults["frame_rate"]
      job["resolution"] overrides defaults["resolution"]
      job["frame_window"] overrides defaults["frame_window"]

    Note: FrameStride is intentionally not passed to SaveAnimation,
    because many ParaView versions do not support it there.
    """
    frame_rate = job.get("frame_rate", defaults.get("frame_rate"))
    resolution = job.get("resolution", defaults.get("resolution", [1920, 1080]))
    frame_window = job.get("frame_window", defaults.get("frame_window"))

    params = {
        "ImageResolution": resolution,
    }

    if frame_rate is not None:
        params["FrameRate"] = frame_rate

    if frame_window is not None:
        params["FrameWindow"] = frame_window

    # Optional writer/settings pass-through.
    # Job-level values override defaults.
    for src, dst in [
        ("quality", "Quality"),
        ("compression", "Compression"),
        ("override_color_palette", "OverrideColorPalette"),
    ]:
        value = job.get(src, defaults.get(src))
        if value is not None:
            params[dst] = value

    return params


def _save_animation(job, defaults, output_dir):
    scene = GetAnimationScene()
    try:
        scene.UpdateAnimationUsingDataTimeSteps()
    except Exception as exc:
        print(f"WARNING: could not update animation from data time steps: {exc}", file=sys.stderr)

    target = _get_target(job)
    view = _get_render_view()
    _apply_camera_and_view(view, job, defaults, reset_default=False)
    RenderAllViews()

    output_name = job.get("output") or (job["name"] + defaults.get("extension", ".ogv"))
    output_path = Path(output_name)
    if not output_path.is_absolute():
        output_path = output_dir / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing {output_path}")
    SaveAnimation(str(output_path), target, **_animation_params(job, defaults))


def _resolve_state_filenames(job, base_dir):
    """Resolve optional LoadState(..., filenames=[...]) overrides."""
    overrides = []
    root = Path(_resolve(job.get("data_dir", "."), base_dir))
    for entry in job.get("filenames", []):
        item = dict(entry)
        for prop in ("FileName", "FileNames"):
            if prop in item:
                value = item[prop]
                if isinstance(value, list):
                    item[prop] = [_resolve(v, root) for v in value]
                else:
                    item[prop] = _resolve(value, root)
        overrides.append(item)
    return overrides


def render_state_job(job, defaults, base_dir, output_dir):
    _reset()
    state_path = _resolve(job["state"], base_dir)
    kwargs = {}
    if job.get("data_dir"):
        kwargs["data_directory"] = _resolve(job["data_dir"], base_dir)
        kwargs["restrict_to_data_directory"] = bool(job.get("restrict_to_data_directory", True))
    if job.get("filenames"):
        kwargs["filenames"] = _resolve_state_filenames(job, base_dir)
    print(f"Loading state {state_path}")
    LoadState(state_path, **kwargs)
    _save_animation(job, defaults, output_dir)


def render_mesh_job(job, defaults, base_dir, output_dir):
    _reset()
    files = _expand_files(job["files"], base_dir)
    reader = OpenDataFile(files if len(files) > 1 else files[0])
    if reader is None:
        raise RuntimeError(f"ParaView could not open files for job {job['name']}")

    view = _get_render_view()
    display = Show(reader, view)
    _safe_set(display, "Representation", job.get("representation", "Surface"))

    color_by = job.get("color_by")
    if color_by:
        assoc = job.get("color_association", "POINTS")
        ColorBy(display, (assoc, color_by))
        display.RescaleTransferFunctionToDataRange(True, False)
        display.SetScalarBarVisibility(view, True)
    elif "color" in job:
        _safe_set(display, "DiffuseColor", job["color"])

    _apply_camera_and_view(view, job, defaults, reset_default=True)
    _save_animation(job, defaults, output_dir)


def render_csv_glyph_job(job, defaults, base_dir, output_dir):
    _reset()
    files = _expand_files(job["files"], base_dir)

    reader = CSVReader(FileName=files)
    _safe_set(reader, "HaveHeaders", int(job.get("have_headers", True)))
    _safe_set(reader, "DetectNumericColumns", int(job.get("detect_numeric_columns", True)))
    if job.get("field_delimiter") is not None:
        _safe_set(reader, "FieldDelimiterCharacters", job["field_delimiter"])
    reader.UpdatePipelineInformation()

    points = TableToPoints(Input=reader)
    _safe_set(points, "XColumn", job.get("x", "x"))
    _safe_set(points, "YColumn", job.get("y", "y"))
    _safe_set(points, "ZColumn", job.get("z", "z"))
    _safe_set(points, "a2DPoints", int(job.get("two_d", False)))
    _safe_set(points, "KeepAllDataArrays", int(job.get("keep_all_data_arrays", True)))

    glyph_cfg = job.get("glyph", {})
    glyph = Glyph(Input=points)
    _safe_set(glyph, "GlyphType", glyph_cfg.get("type", "Sphere"))
    _safe_set(glyph, "GlyphMode", glyph_cfg.get("mode", "All Points"))
    _safe_set(glyph, "ScaleFactor", glyph_cfg.get("scale_factor", 1.0))
    if glyph_cfg.get("max_points") is not None:
        _safe_set(glyph, "MaximumNumberOfSamplePoints", int(glyph_cfg["max_points"]))

    assoc = glyph_cfg.get("association", "POINTS")
    if glyph_cfg.get("scale_array"):
        _safe_set(glyph, "ScaleArray", [assoc, glyph_cfg["scale_array"]])
    else:
        _safe_set(glyph, "ScaleArray", [assoc, "No scale array"])
    if glyph_cfg.get("orientation_array"):
        _safe_set(glyph, "OrientationArray", [assoc, glyph_cfg["orientation_array"]])
    else:
        _safe_set(glyph, "OrientationArray", [assoc, "No orientation array"])

    view = _get_render_view()
    display = Show(glyph, view)
    _safe_set(display, "Representation", "Surface")

    color_by = job.get("color_by") or glyph_cfg.get("color_by")
    if color_by:
        color_assoc = job.get("color_association", assoc)
        ColorBy(display, (color_assoc, color_by))
        display.RescaleTransferFunctionToDataRange(True, False)
        display.SetScalarBarVisibility(view, True)
    elif "color" in job:
        _safe_set(display, "DiffuseColor", job["color"])

    _apply_camera_and_view(view, job, defaults, reset_default=True)
    _save_animation(job, defaults, output_dir)


def main(argv):
    if len(argv) != 2:
        print("Usage: pvpython paraview_render_all.py render_jobs.json", file=sys.stderr)
        return 2

    manifest_path = Path(argv[1]).resolve()
    base_dir = manifest_path.parent
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    defaults = manifest.get("defaults", {})
    output_dir = Path(_resolve(defaults.get("output_dir", "movies"), base_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    handlers = {
        "state": render_state_job,
        "mesh": render_mesh_job,
        "csv_glyph": render_csv_glyph_job,
    }

    jobs = manifest.get("jobs", [])
    if not jobs:
        raise RuntimeError("Manifest contains no jobs.")

    for idx, job in enumerate(jobs, start=1):
        name = job.get("name", f"job_{idx}")
        job["name"] = name
        kind = job.get("kind", "state")
        if kind not in handlers:
            raise RuntimeError(f"Unknown job kind {kind!r} for {name}")
        print(f"\n=== [{idx}/{len(jobs)}] {name} ({kind}) ===")
        handlers[kind](job, defaults, base_dir, output_dir)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
