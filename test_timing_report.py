import contextlib
import importlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from timing_report import generate_timing_report


class TimingReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for folder in ("known_timing", "results"):
            (self.root / folder).mkdir()

    def log(self, folder, name, text):
        (self.root / folder / name).write_text(text, encoding="utf-8")

    def report(self, config=None):
        path = generate_timing_report(config or {}, self.root, self.root / "movies")
        return path.read_text(encoding="utf-8")

    def test_comparison_last_match_and_custom_pattern(self):
        for name, known, new in (("Fast", "100", "8e1"), ("Slow", "10", "15"), ("Same", "2", "2")):
            for folder, value in (("known_timing", known), ("results", new)):
                self.log(folder, f"DEMdemo_{name}.txt", "999 seconds (wall time) to finish the simulation\n"
                         f"{value} seconds (wall time) to finish the simulation\n")
        self.log("known_timing", "DEMdemo_Custom.txt", "Elapsed: 4s\n")
        self.log("results", "DEMdemo_Custom.txt", "Elapsed: 1s\n")
        result = self.report({"patterns": {"DEMdemo_Custom.txt": r"Elapsed: (?P<seconds>\d+)s"}})
        self.assertIn("| 100 | 80 | -20.00% | faster |", result)
        self.assertIn("| 10 | 15 | +50.00% | slower |", result)
        self.assertIn("| 2 | 2 | +0.00% | unchanged |", result)
        self.assertIn("| 4 | 1 | -75.00% | faster |", result)

    def test_missing_invalid_and_empty_data(self):
        self.log("known_timing", "DEMdemo_Missing.txt", "unused")
        for name, value in (("NoLine", "unrelated"), ("Zero", "0"), ("Negative", "-5"), ("Overflow", "1e999")):
            for folder in ("known_timing", "results"):
                self.log(folder, f"DEMdemo_{name}", f"{value} seconds (wall time) to finish the simulation")
        result = self.report()
        self.assertIn("Compared: 0. Skipped: 5.", result)
        self.assertIn("missing new log", result)
        self.assertIn("no matching timing line", result)
        self.assertIn("No comparable timing data found.", result)
        self.assertIn("Compared: 0. Skipped: 0.", self.report({"known_dir": "absent", "new_dir": "also_absent"}))

    def test_rotating_drum_standard_completion_message(self):
        self.log("known_timing", "DEMdemo_RotatingDrum.txt",
                 "5247.43 seconds (wall time) to finish the simulation\n")
        self.log("results", "DEMdemo_RotatingDrum.txt",
                 "9161.78 seconds (wall time) to finish the simulation\n"
                 "9000 seconds (wall time, DoDynamics only) to finish the simulation\n")
        for config in ({}, self.example_timing_config()):
            with self.subTest(config=config):
                result = self.report(config)
                self.assertIn("Compared: 1. Skipped: 0.", result)
                self.assertIn("| 5247.43 | 9161.78 |", result)

    def example_timing_config(self):
        manifest = Path(__file__).with_name("render_jobs.example.json")
        return json.loads(manifest.read_text())["timing"]

    def test_new_known_logs_are_discovered_with_example_patterns(self):
        messages = {
            "DrumCubes": ("8386.59 seconds (wall time) to finish the simulation\n"
                          "8386.24 seconds (wall time, DoDynamics only) to finish the simulation", "8386.59"),
            "ResponseAngleMesh": ("599.342 seconds (wall time) to finish the simulation", "599.342"),
            "HopperSphereMeshedCylinder": ("Simulated 8.2 s in 17454.8 s wall time", "17454.8"),
            "MeshFalling": ("kT total active time: 7.97607244 seconds\n"
                            "dT total active time: 5.77271717 seconds", "5.77271717"),
        }
        for name, (message, _) in messages.items():
            for folder in ("known_timing", "results"):
                self.log(folder, f"DEMdemo_{name}.txt", message)
        result = self.report(self.example_timing_config())
        self.assertIn("Compared: 4. Skipped: 0.", result)
        for name, (_, seconds) in messages.items():
            self.assertIn(f"| DEMdemo_{name}.txt | {seconds} | {seconds} |", result)

    def test_configuration_validation_and_disable(self):
        self.assertIsNone(generate_timing_report({"enabled": False}, self.root, self.root / "out"))
        self.assertFalse((self.root / "out").exists())
        with self.assertRaisesRegex(ValueError, "named group"):
            self.report({"pattern": r"(\d+) seconds"})

    def test_render_failure_still_writes_report(self):
        # ParaView rendering is stubbed; exercise the real render-all orchestration.
        fake = {"paraview": types.ModuleType("paraview"), "paraview.simple": types.ModuleType("paraview.simple")}
        with patch.dict(sys.modules, fake):
            renderer = importlib.import_module("paraview_render_all")
        manifest = self.root / "jobs.json"
        manifest.write_text(json.dumps({"jobs": [{"name": "Broken", "kind": "state"}]}))
        with patch.object(renderer, "render_state_job", side_effect=RuntimeError("render failed")):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(renderer.main(["render", str(manifest)]), 1)
        self.assertTrue((self.root / "movies" / "timing_report.md").exists())


if __name__ == "__main__":
    unittest.main()
