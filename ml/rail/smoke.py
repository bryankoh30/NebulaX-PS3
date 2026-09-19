"""Fresh-process handoff checks on real training recordings, never Test."""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .data import CLASSES, training_labels
from .features import CACHE, PACKAGE
from .inference import DEFAULT_ARTIFACT_DIR


def smoke(artifacts=None):
    root, labels = training_labels()
    artifacts = (Path(artifacts) if artifacts else DEFAULT_ARTIFACT_DIR).resolve()
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=CACHE) as temporary:
        work = Path(temporary)
        inputs = work / "inputs"
        inputs.mkdir()
        for label in CLASSES:
            filename = labels.loc[labels.label == label, "filename"].iloc[0]
            shutil.copyfile(root / "Train" / filename, inputs / filename)
        paths = sorted(inputs.glob("*.csv"), key=lambda p: p.name)
        env = os.environ.copy()
        env["DATASET_ROOT"] = str(work / "absent-dataset")
        env["PYTHONPATH"] = str(PACKAGE.parents[1])
        for name, input_path in [("single", paths[0]), ("batch", inputs)]:
            output = work / f"{name}_predictions.csv"
            command = [sys.executable, "-m", "ml.rail.predict", "--input", str(input_path),
                       "--output", str(output), "--artifacts", str(artifacts)]
            subprocess.run(command, cwd=work, env=env, check=True)
            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                assert reader.fieldnames == ["file_id", "prediction"]
                rows = list(reader)
            expected = paths[:1] if name == "single" else paths
            assert [r["file_id"] for r in rows] == [p.name for p in expected]
            assert all(r["prediction"] in CLASSES for r in rows)
        code = """
import json, sys
from pathlib import Path
from ml.rail.inference import predict_rail
paths = sorted(Path(sys.argv[1]).glob('*.csv'), key=lambda p: p.name)
records = predict_rail(paths, sys.argv[2])
json.dumps(records)
assert all(type(r['prediction']) is str for r in records)
assert not any(n in sys.modules for n in ['ml.config', 'ml.rail.train', 'ml.rail.evaluate', 'ml.door', 'ml.acv', 'ml.shm'])
Path(sys.argv[3]).write_text(json.dumps(records), encoding='utf-8')
"""
        result_path = work / "api.json"
        subprocess.run([sys.executable, "-c", code, str(inputs), str(artifacts), str(result_path)], cwd=work, env=env, check=True)
        assert json.loads(result_path.read_text()) == rows
    print("Fresh-process single-file CLI, directory CLI and Python API passed; exact CSV, original names, invalid DATASET_ROOT, unrelated cwd, no other subsystem imports.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path)
    smoke(parser.parse_args().artifacts)
