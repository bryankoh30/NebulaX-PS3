"""Five-fold file-level out-of-fold comparison; organiser Test is never read."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from .data import CLASSES, digest
from .features import FEATURE_VERSION, PACKAGE, training_features
from .models import make_model
from .provenance import model_source_hashes, peak_memory_bytes


def evaluate(dataset_root=None):
    start = time.perf_counter()
    values, labels, folds, names, split = training_features(dataset_root)
    extraction_seconds = time.perf_counter() - start
    report = {'feature_version': FEATURE_VERSION, 'split_sha256': digest(PACKAGE / 'validation_split.json'),
              'model_source_sha256': model_source_hashes(),
              'source_hash_algorithm': 'sha256-crlf-normalized-to-lf',
              'classes': CLASSES, 'feature_count': len(names), 'feature_matrix_bytes': values.nbytes,
              'feature_loading_seconds': extraction_seconds, 'models': {}}
    for name in ['always_normal', 'random_forest', 'extra_trees']:
        model_start = time.perf_counter()
        predictions = np.empty(len(labels), dtype=object)
        scores = []
        for fold in range(5):
            train, validation = folds != fold, folds == fold
            model = make_model(name)
            model.fit(values[train], labels[train])
            predictions[validation] = model.predict(values[validation])
            score = f1_score(labels[validation], predictions[validation], labels=CLASSES, average='macro', zero_division=0)
            scores.append(float(score))
            print(f'{name} fold {fold}: Macro F1={score:.6f}', flush=True)
        matrix = confusion_matrix(labels, predictions, labels=CLASSES)
        errors = {}
        for true in CLASSES:
            for predicted in CLASSES:
                if true != predicted:
                    indices = np.flatnonzero((labels == true) & (predictions == predicted))
                    errors[f'{true} -> {predicted}'] = [split['recordings'][i]['file_id'] for i in indices]
        report['models'][name] = {
            'macro_f1': float(f1_score(labels, predictions, labels=CLASSES, average='macro', zero_division=0)),
            'per_class': classification_report(labels, predictions, labels=CLASSES, output_dict=True, zero_division=0),
            'confusion_matrix': matrix.tolist(), 'fold_macro_f1': scores,
            'mean_fold_macro_f1': float(np.mean(scores)), 'std_fold_macro_f1': float(np.std(scores)),
            'errors': errors, 'fit_predict_seconds': time.perf_counter() - model_start,
        }
    candidates = ['random_forest', 'extra_trees']
    report['selected_model'] = max(candidates, key=lambda n: report['models'][n]['macro_f1'])
    report['selection_note'] = 'Select pooled OOF Macro F1; Random Forest wins exact ties. Same folds used for selection and reporting, so not an unbiased post-selection estimate.'
    report['elapsed_seconds'] = time.perf_counter() - start
    report['peak_process_memory_bytes'] = peak_memory_bytes()
    (PACKAGE / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'selected_model': report['selected_model'], 'macro_f1': {n: r['macro_f1'] for n, r in report['models'].items()}}))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-root', type=Path)
    args = parser.parse_args()
    evaluate(args.dataset_root)


if __name__ == '__main__':
    main()
