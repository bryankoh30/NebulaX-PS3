# NebulaX PS3

Subsystem-first workspace for Door, Rail Corrugation, ACV, and SHM.

**Status: scaffold only.** No models have been trained. Training, evaluation, and prediction commands deliberately report that implementation is pending. No backend or frontend is included yet.

## Start Here

Read [plan.md](plan.md) and [contracts/model.md](contracts/model.md) before editing.

| Owner | Packages | Plan phases | Branches |
| --- | --- | --- | --- |
| A | `ml/door/` | D1-D4 | `feat/door` |
| B | `ml/rail/` and shared Python setup | R1-R4 | `feat/rail` |
| C | `ml/shm/` and `ml/acv/` | S1-S4, V1-V4 | `feat/shm`, then `feat/acv` |

Backend/frontend work starts only after all four packages pass the model handoff gate. C should establish a SHM baseline, then an ACV baseline, before refining both.

## Python Setup

Use Python 3.11 or newer. Run from this repository root. The scaffold was checked with Python 3.12; teammates should agree one version before training and sharing model artifacts.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit your local `.env` to point to the organiser repository's `PS3/02_Datasets` directory. Each machine has its own path. This machine's local `.env` is already configured; do not overwrite it unless relocating the data.

```dotenv
DATASET_ROOT=C:/path/to/NebulaX-Hackathon-ProblemStatement/PS3/02_Datasets
```

On macOS/Linux use `.venv/bin/python` instead of the Windows Python path. Activation is optional. The virtual environment and dependencies are not included in Git.

## Working Independently

Start each branch from current `main`:

```text
git switch main
git pull --ff-only
git switch -c feat/door
```

Use your subsystem's branch name. Keep edits in your package and request shared dependency/contract changes from B. Submit small PRs for working baselines, then finish evaluation and artifact handoff. Keep ACV and SHM PRs separate.

Give your agent this instruction, changing the role and phases as needed:

```text
Read plan.md and contracts/model.md. You are Agent A (Door).
Implement only phases D1-D4 inside ml/door/ and the shared handoff requirements.
Do not build backend or frontend code. Report commands, checks, and limitations.
```

## Included References

`PS3/` contains the organiser's specification, all subsystem reference kits, Rail images, and example CSV schemas. Example predictions are illustrative placeholders, not training labels or actual model output. The copied references remain unchanged.

Datasets stay in the organiser repository. Do not commit them, generated model binaries, local environment files, or prediction output. Development code and artifact manifests are committed; transfer trained artifacts separately and document how to regenerate them.

## Scaffold Commands

These help commands work now:

```text
python -m ml.door.predict --help
python -m ml.rail.predict --help
python -m ml.acv.predict --help
python -m ml.shm.predict --help
```

Actual training, evaluation, and inference are intentionally unimplemented. Each owner must replace the clear errors with real behaviour, add focused tests, and update their package README with verified commands and scores.
