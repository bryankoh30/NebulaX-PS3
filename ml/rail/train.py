"""Train a development baseline or refit the best cross-validated Rail model."""
import argparse
import importlib.metadata
import json
import platform
from pathlib import Path

import joblib
from sklearn.metrics import f1_score

from .data import CHANNELS, CLASSES, digest
from .features import FEATURE_VERSION, PACKAGE, training_features
from .inference import DEFAULT_ARTIFACT_DIR
from .models import make_model
from .provenance import model_source_hashes


def dependencies():
    names = ['numpy', 'pandas', 'scipy', 'scikit-learn', 'joblib', 'python-dotenv']
    return {'python': platform.python_version(), **{n: importlib.metadata.version(n) for n in names}}


def train(dataset_root=None, artifacts=None, baseline=False):
    if baseline:
        selected = 'random_forest'
    else:
        evaluation_path = PACKAGE / 'evaluation.json'
        if not evaluation_path.is_file():
            raise FileNotFoundError('Run python -m ml.rail.evaluate before the final fit')
        report = json.loads(evaluation_path.read_text(encoding='utf-8'))
        if report['feature_version'] != FEATURE_VERSION or report['split_sha256'] != digest(PACKAGE / 'validation_split.json'):
            raise ValueError('Evaluation is stale; run python -m ml.rail.evaluate again')
        if report['model_source_sha256'] != model_source_hashes():
            raise ValueError('Model code changed since evaluation; reevaluate before the final fit')
        selected = report['selected_model']
    values, labels, folds, names, split = training_features(dataset_root)
    mask = folds != 0 if baseline else folds >= 0
    model = make_model(selected)
    model.fit(values[mask], labels[mask])
    directory = Path(artifacts) if artifacts is not None else (DEFAULT_ARTIFACT_DIR / 'baseline' if baseline else DEFAULT_ARTIFACT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    if baseline:
        baseline_scores = {}
        for name in ['always_normal', 'random_forest', 'extra_trees']:
            candidate = model if name == selected else make_model(name).fit(values[mask], labels[mask])
            prediction = candidate.predict(values[~mask])
            baseline_scores[name] = float(f1_score(labels[~mask], prediction, labels=CLASSES, average='macro', zero_division=0))
        (directory / 'baseline_metrics.json').write_text(json.dumps(baseline_scores, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'development_fold_0_macro_f1': baseline_scores}), flush=True)
    bundle = {'model': model, 'feature_version': FEATURE_VERSION, 'feature_names': names,
              'classes': CLASSES, 'dependencies': dependencies()}
    joblib.dump(bundle, directory / 'model.joblib', compress=3)
    manifest = {
        'schema_version': 1, 'subsystem': 'rail', 'stage': 'development_baseline' if baseline else 'final',
        'model': selected, 'model_parameters': model.get_params(), 'training_recordings': int(mask.sum()),
        'feature_version': FEATURE_VERSION, 'feature_names': names, 'classes': CLASSES,
        'preprocessing': 'Stateless per-recording features; no fitted scaling, imputation or selection',
        'channel_mapping': CHANNELS, 'sample_rate_hz': 10000, 'rows_per_recording': 10000,
        'dependencies': dependencies(), 'artifact_file': 'model.joblib',
        'artifact_sha256': digest(directory / 'model.joblib'),
        'split_sha256': digest(PACKAGE / 'validation_split.json'),
        'source_sha256': {p.name: digest(p) for p in sorted(PACKAGE.glob('*.py'))},
        'regeneration': ['python -m ml.rail.inspect', 'python -m ml.rail.evaluate', 'python -m ml.rail.train'],
        'trusted_artifacts_only': 'joblib/pickle loading executes code; use only the team-generated artifact',
    }
    if not baseline:
        manifest['validation_macro_f1'] = report['models'][selected]['macro_f1']
        manifest['selection_metric'] = 'pooled out-of-fold Macro F1, fixed seed-42 five-fold split'
    text = json.dumps(manifest, indent=2) + '\n'
    (directory / 'manifest.json').write_text(text, encoding='utf-8')
    if not baseline:
        (PACKAGE / 'artifact_manifest.json').write_text(text, encoding='utf-8')
    print(json.dumps({'model': selected, 'training_recordings': int(mask.sum()), 'artifact': str(directory / 'model.joblib')}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path)
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--baseline', action='store_true', help='R2: fit Random Forest on folds 1-4; leave fold 0 untouched')
    args = parser.parse_args()
    train(args.dataset_root, args.artifacts, args.baseline)


if __name__ == '__main__':
    main()
