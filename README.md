# ParaView Visualization

Batch rendering helpers for turning DEM simulation results into ParaView movies.

The repository stores the rendering script, ParaView state files, and example
job manifest. Large local assets are intentionally not tracked:

- `ParaView-*` application bundles
- `results/` simulation output directories
- `movies/` rendered animations

## Requirements

- ParaView with Python support. The example command below uses the local
  `ParaView-5.10.1-MPI-Linux-Python3.9-x86_64` bundle.
- Simulation result folders matching the paths in `render_jobs.example.json`.

## Usage

From the repository root, run this after unpacking a ParaView binary tarball in
the current directory. Adjust the ParaView folder name if you use a different
version.

```bash
ParaView-5.10.1-MPI-Linux-Python3.9-x86_64/bin/pvpython --force-offscreen-rendering paraview_render_all.py render_jobs.example.json
```

By default, rendered movies are written to `movies/`.

Each run also writes `movies/timing_report.md`, comparing simulation runtimes
from `known_timing/` and `results/` (alongside the new demo output folders). The report is generated before rendering,
so it is available even if a movie job fails. It matches logs by exact filename
(`DEMdemo_*` by default), independently of the movie job list. Missing files,
missing timing lines, and invalid/nonpositive runtimes are skipped and listed
in the report. A run with no comparable logs still writes a report.

The table shows known/new seconds, percentage runtime change, and whether the
new run is faster, slower, or unchanged. Percentage change is
`100 * (new / known - 1)`; negative values mean faster.

### Timing configuration

The manifest's optional top-level `timing` object controls the comparison:

- `enabled`: defaults to `true`; set to `false` to disable the report.
- `known_dir`, `new_dir`: default to `known_timing` and `results`.
- `file_glob`: defaults to `DEMdemo_*`; filenames must match between folders.
- `output`: defaults to `timing_report.md` inside the movie output directory.
- `pattern`: Python regular expression searched on each log line. It must
  capture seconds in a named group, `(?P<seconds>...)`. The default matches
  `123.45 seconds (wall time) to finish the simulation` and accepts decimal
  and scientific notation.
- `patterns`: optional map of exact log filenames to replacement patterns,
  used for both the known and new log. The example manifest includes overrides
  for Plow, Centrifuge, and RotatingDrum's different completion messages.
  HopperSphereCylinder uses `dT total active time: XXXXX seconds` in both logs.

All configured relative paths are resolved from the manifest directory. Regex
backslashes must be escaped in JSON (for example, `\\s` for regex `\s`). If
several lines match, the last match is used; narrow the pattern if a log
contains multiple distinct simulation phases. Invalid patterns or report-write
errors are reported without stopping movie jobs, but cause exit code `1`.

If one job fails, for example because its result directory is missing, the
script logs that failure and continues with the remaining jobs. At the end it
prints a completed/failed summary. The process exits with code `1` if any job
failed after all jobs have been attempted.

For state-file jobs, the script also expands numbered file series saved in the
`.pvsm` file to the full matching series in each job's `data_dir`. This keeps a
state file that was saved with only a short preview range from limiting the
rendered movie. Use `frame_window` in the manifest to choose the output frame
range after that expansion.

## Render Jobs

`paraview_render_all.py` reads a JSON manifest with a `defaults` section and a
`jobs` array. Each job can load a ParaView state file or open mesh/CSV data
directly. The included `render_jobs.example.json` currently renders these
state-based jobs:

| Job | State file | Result directory | Output |
| --- | --- | --- | --- |
| `FlexibleMesh` | `states/FlexibleMesh.pvsm` | `results/DemoOutput_FlexibleMesh` | `movies/FlexibleMesh.ogv` |
| `Electrostatic` | `states/Electrostatic.pvsm` | `results/DemoOutput_Electrostatic` | `movies/Electrostatic.ogv` |
| `GameOfLife` | `states/GameOfLife.pvsm` | `results/DemoOutput_GameOfLife` | `movies/GameOfLife.ogv` |
| `HopperSphereMeshedCylinder` | `states/HopperSphereMeshedCylinder.pvsm` | `results/DemoOutput_HopperSphereMeshedCylinder` | `movies/HopperSphereMeshedCylinder.ogv` |
| `BallDrop` | `states/BallDrop.pvsm` | `results/DemoOutput_BallDrop` | `movies/BallDrop.ogv` |
| `BallDrop2D` | `states/BallDrop2D.pvsm` | `results/DemoOutput_BallDrop2D` | `movies/BallDrop2D.ogv` |
| `Centrifuge` | `states/Centrifuge.pvsm` | `results/DemoOutput_Centrifuge` | `movies/Centrifuge.ogv` |
| `Mixer` | `states/Mixer.pvsm` | `results/DemoOutput_Mixer` | `movies/Mixer.ogv` |
| `Repose2D` | `states/Repose2D.pvsm` | `results/DemoOutput_Repose2D` | `movies/Repose2D.ogv` |
| `Sieve` | `states/Sieve.pvsm` | `results/DemoOutput_Sieve` | `movies/Sieve.ogv` |
| `SolarSystem` | `states/SolarSystem.pvsm` | `results/DemoOutput_SolarSystem` | `movies/Repose2D.ogv` |
| `WheelDPSimplified` | `states/WheelDPSimplified.pvsm` | `results/DemoOutput_WheelDPSimplified` | `movies/WheelDPSimplified.ogv` |

To customize a run, copy or edit the manifest and update the state paths,
result directories, output names, frame rate, resolution, or camera settings.

## GitHub Setup

This local checkout is initialized on `main` with `origin` set to
`https://github.com/Ruochun/ParaView-Visualization.git`.

If you need to recreate that setup elsewhere:

```bash
git remote add origin https://github.com/Ruochun/ParaView-Visualization.git
git branch -M main
```

For the first publish:

```bash
git add .
git commit -m "Initial ParaView visualization setup"
git push -u origin main
```
