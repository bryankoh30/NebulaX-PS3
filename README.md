# NebulaX PS3

Predictive-maintenance prototype for Door, Rail Corrugation, ACV, and SHM.

**Status:** all four model packages, the FastAPI backend, and the React frontend
are implemented on `main`. Runtime model artifacts remain machine-local and
must be installed explicitly; see [backend/README.md](backend/README.md).
Code-level integration and regression checks do not imply every machine has
the frozen model artifacts installed.

## Start Here

Read [plan.md](plan.md) and [contracts/model.md](contracts/model.md) before editing.

| Owner | Packages | Plan phases | Branches |
| --- | --- | --- | --- |
| A | `ml/door/` | D1-D4 | `feat/door` |
| B | `ml/rail/` and shared Python setup | R1-R4 | `feat/rail` |
| C | `ml/shm/` and `ml/acv/` | S1-S4, V1-V4 | `feat/acv-shm` |

The backend calls these frozen inference packages directly and never trains
during a request. See [contracts/api.md](contracts/api.md) for the frontend
contract.

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

The three agent branches are published on GitHub. In your own clone, fetch them and switch to your assigned branch (A shown):

```text
git fetch origin
git switch feat/door
git merge origin/main
```

Use `feat/rail` for B or `feat/acv-shm` for C. Keep edits in your assigned packages and request shared dependency/contract changes from B. Submit small PRs for working baselines, then finish evaluation and artifact handoff. C uses one branch and may submit one PR covering both packages; keep ACV and SHM changes in separate commits. After each model merge, fetch and merge updated `origin/main` into your active branch before continuing.

Give your agent this instruction, changing the role and phases as needed:

```text
Read plan.md and contracts/model.md. You are Agent A (Door).
Implement only phases D1-D4 inside ml/door/ and the shared handoff requirements.
Do not build backend or frontend code. Report commands, checks, and limitations.
```

## Included References

`PS3/` contains the organiser's specification, all subsystem reference kits, Rail images, and example CSV schemas. Example predictions are illustrative placeholders, not training labels or actual model output. The copied references remain unchanged.

Datasets stay in the organiser repository. Do not commit them, generated model binaries, local environment files, or prediction output. Development code and artifact manifests are committed; transfer trained artifacts separately and document how to regenerate them.

## Model Commands

```text
python -m ml.door.predict --help
python -m ml.rail.predict --help
python -m ml.acv.predict --help
python -m ml.shm.predict --help
```

Each package README documents its training, evaluation, artifact, inference,
and validation commands.

## Backend

Install the root requirements and start the API from the repository root:

```text
python -m pip install -r requirements.txt
python -m backend
```

Open `http://127.0.0.1:8000/docs` for the interactive API. Runtime uploads and
SQLite state stay under ignored `backend/runtime/`. See
[backend/README.md](backend/README.md) for configuration and verification.
