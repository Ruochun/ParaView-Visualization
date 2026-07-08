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
