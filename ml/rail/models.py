"""Fixed statistical baseline candidates, without dataset-fitted preprocessing."""
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier


def make_model(name):
    settings = dict(n_estimators=500, class_weight="balanced", random_state=42,
                    n_jobs=2, max_features="sqrt", min_samples_leaf=1)
    if name == "random_forest":
        return RandomForestClassifier(**settings)
    if name == "extra_trees":
        return ExtraTreesClassifier(**settings)
    if name == "always_normal":
        return DummyClassifier(strategy="constant", constant="Normal")
    raise ValueError(f"Unknown model: {name}")
