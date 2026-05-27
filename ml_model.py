"""
Exploratory ML for Injury_Label.

⚠️  CRITICAL CONTEXT
The dataset contains only 2 positive injury cases in 1 800 rows.
Any model trained on this is exploratory only. We use SMOTE-style
oversampling to expose patterns, NEVER to claim predictive validity.

The page that consumes this module surfaces those caveats prominently.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_auc_score, precision_recall_curve, roc_curve,
)


DEFAULT_FEATURES = [
    "Total_Distance", "HSR", "Sprint_Distance", "Accelerations", "Decelerations",
    "RPE", "Session_Load", "Acute_Load", "Chronic_Load", "ACWR",
    "HRV_RMSSD", "Resting_HR",
    "Fatigue_Score", "Soreness_Score", "Sleep_Quality", "CMJ_Height",
    "CMJ_Height_PctChange", "HRV_RMSSD_PctChange",
]


def _oversample_minority(X: pd.DataFrame, y: pd.Series,
                          target_ratio: float = 0.2,
                          random_state: int = 42) -> tuple[pd.DataFrame, pd.Series]:
    """
    Naive duplicating oversampler — preferred over importing imbalanced-learn
    to keep the install footprint small. We replicate minority rows with
    small Gaussian jitter to avoid identical copies.
    """
    rng = np.random.default_rng(random_state)
    pos = y[y == 1].index.tolist()
    neg = y[y == 0].index.tolist()
    if not pos:
        return X, y
    target_pos = int(len(neg) * target_ratio / (1 - target_ratio))
    if target_pos <= len(pos):
        return X, y
    extra = target_pos - len(pos)
    sampled = rng.choice(pos, size=extra, replace=True)
    X_extra = X.loc[sampled].copy().reset_index(drop=True)
    jitter = rng.normal(loc=0.0, scale=0.02, size=X_extra.shape)
    X_extra = X_extra * (1.0 + jitter)
    y_extra = pd.Series([1] * extra)
    X_new = pd.concat([X.reset_index(drop=True), X_extra], ignore_index=True)
    y_new = pd.concat([y.reset_index(drop=True), y_extra], ignore_index=True)
    return X_new, y_new


def train_injury_model(df: pd.DataFrame,
                       model_name: str = "Random Forest",
                       features: list[str] | None = None,
                       oversample: bool = True,
                       random_state: int = 42) -> dict:
    """
    Train + evaluate a single model. Returns a dict with everything the
    page needs to render results without re-running anything.
    """
    features = features or DEFAULT_FEATURES
    features = [f for f in features if f in df.columns]
    if not features:
        return {"status": "insufficient", "message": "No valid features selected."}
    sub = df.dropna(subset=features + ["Injury_Label"]).copy()
    if sub.empty:
        return {"status": "insufficient", "message": "No rows after dropping missing feature values."}
    if sub["Injury_Label"].nunique() < 2:
        return {"status": "insufficient",
                "message": "Model cannot be trained because the filtered data contains only one injury class."}
    if sub["Injury_Label"].sum() < 2:
        return {"status": "insufficient",
                "message": "Fewer than 2 injury cases — model not trained."}

    X = sub[features]
    y = sub["Injury_Label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=random_state,
    )

    if oversample:
        X_train_os, y_train_os = _oversample_minority(X_train, y_train,
                                                     target_ratio=0.20,
                                                     random_state=random_state)
    else:
        X_train_os, y_train_os = X_train, y_train

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train_os)
    X_test_sc = scaler.transform(X_test)

    if model_name == "Logistic Regression":
        model = LogisticRegression(max_iter=1000, class_weight="balanced",
                                   random_state=random_state)
    elif model_name == "Decision Tree":
        model = DecisionTreeClassifier(max_depth=5, class_weight="balanced",
                                       random_state=random_state)
    else:
        model = RandomForestClassifier(n_estimators=200, max_depth=6,
                                       class_weight="balanced",
                                       random_state=random_state)

    model.fit(X_train_sc, y_train_os)
    y_pred = model.predict(X_test_sc)
    try:
        y_proba = model.predict_proba(X_test_sc)[:, 1]
    except Exception:
        y_proba = None

    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    report = classification_report(y_test, y_pred, output_dict=True,
                                   zero_division=0)
    auc = None
    fpr = tpr = None
    prec_curve = recall_curve = None
    if y_proba is not None and y_test.nunique() == 2:
        try:
            auc = roc_auc_score(y_test, y_proba)
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            prec_curve, recall_curve, _ = precision_recall_curve(y_test, y_proba)
        except Exception:
            pass

    if hasattr(model, "feature_importances_"):
        importances = pd.Series(model.feature_importances_, index=features)
    elif hasattr(model, "coef_"):
        importances = pd.Series(np.abs(model.coef_[0]), index=features)
    else:
        importances = pd.Series([0.0] * len(features), index=features)
    importances = importances.sort_values(ascending=False)

    return {
        "status": "ok",
        "model": model,
        "model_name": model_name,
        "features": features,
        "n_rows": len(sub),
        "n_injuries": int(y.sum()),
        "injury_prevalence": float(y.mean() * 100),
        "n_train": len(y_train_os),
        "n_test": len(y_test),
        "n_pos_train": int(y_train_os.sum()),
        "n_pos_test": int(y_test.sum()),
        "confusion_matrix": cm,
        "report": report,
        "roc_auc": auc,
        "fpr": fpr,
        "tpr": tpr,
        "pr_precision": prec_curve,
        "pr_recall": recall_curve,
        "feature_importance": importances,
    }


def feature_importance_df(result: dict, top_n: int = 12) -> pd.DataFrame:
    """Return tidy top-N importance frame for plotting."""
    if result.get("status") != "ok":
        return pd.DataFrame(columns=["Feature", "Importance"])
    imp = result["feature_importance"].head(top_n).reset_index()
    imp.columns = ["Feature", "Importance"]
    return imp
