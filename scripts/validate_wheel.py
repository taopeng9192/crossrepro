"""Install a wheel into a new venv and verify it away from the source tree."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv


def find_wheel(directory: Path) -> Path:
    """Return the sole CrossRepro wheel in a build directory."""
    wheels = sorted(directory.glob("crossrepro-*.whl"))
    if not wheels:
        raise FileNotFoundError(f"no CrossRepro wheel found in {directory}")
    if len(wheels) != 1:
        names = ", ".join(wheel.name for wheel in wheels)
        raise ValueError(f"expected one CrossRepro wheel in {directory}, found: {names}")
    return wheels[0]


def validate(wheel: Path) -> dict:
    wheel = wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="crossrepro-wheel-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        # Keep this acceptance check independent of host-wide --user defaults.
        env.pop("PIP_USER", None)
        env["PIP_CONFIG_FILE"] = os.devnull
        env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")
        env["PYTHONUTF8"] = "1"
        subprocess.run([str(python), "-m", "pip", "install", "--no-user", str(wheel)], cwd=root, env=env, check=True)
        executable = scripts / ("crossrepro.exe" if os.name == "nt" else "crossrepro")
        subprocess.run([str(executable), "--help"], cwd=root, env=env, check=True, capture_output=True)
        probe = subprocess.run([str(python), "-I", "-c", "import crossrepro,json; print(json.dumps({'version':crossrepro.__version__,'module':crossrepro.__file__}))"],
                               cwd=root, env=env, check=True, capture_output=True, text=True, encoding="utf-8")
        info = json.loads(probe.stdout)
        if not Path(info["module"]).resolve().is_relative_to(environment.resolve()):
            raise AssertionError("import came from outside the clean virtual environment")
        (root / "fail.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        subprocess.run([str(executable), "collect", "--command-text", "python fail.py"], cwd=root, env=env, check=True, capture_output=True)
        subprocess.run([str(executable), "replay", ".crossrepro/latest/repro.yml"], cwd=root, env=env, check=True, capture_output=True)
        report = json.loads((root / "report.json").read_text(encoding="utf-8"))
        if report["result"]["verdict"] != "REPRODUCED" or report["execution"]["exit_code"] != 7:
            raise AssertionError("installed wheel failed capture/replay")
        return {"wheel": wheel.name, "version": info["version"], "clean_install": "PASS",
                "isolated_import": "PASS", "console_entry_point": "PASS", "capture_replay": "PASS"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("wheel", nargs="?", type=Path)
    input_group.add_argument("--wheel-dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    wheel = find_wheel(args.wheel_dir) if args.wheel_dir else args.wheel
    result = validate(wheel)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
