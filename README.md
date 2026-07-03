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

From the repository root, run:

```bash
ParaView-5.10.1-MPI-Linux-Python3.9-x86_64/bin/pvpython --force-offscreen-rendering paraview_render_all.py render_jobs.example.json
```

By default, rendered movies are written to `movies/`.

## Render Jobs

`paraview_render_all.py` reads a JSON manifest with a `defaults` section and a
`jobs` array. Each job can load a ParaView state file or open mesh/CSV data
directly. The included `render_jobs.example.json` renders:

- `states/FlexibleMesh.pvsm`
- `states/Electrostatic.pvsm`
- `states/GameOfLife.pvsm`

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
