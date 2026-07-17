"""
Evaluation script — generates a full classification report + confusion matrix plot.
Run: python src/evaluate.py --data-path data/raw
"""

import argparse
import glob
import os
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from loguru import logger
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split

from features import OBSERVED_EMOTIONS, extract_feature, get_emotion_from_filename


def evaluate(data_path: str, model_path: str = "models/ser_model.pkl"):
    # Load model
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Load data
    x, y = [], []
    for fpath in glob.glob(os.path.join(data_path, "**/*.wav"), recursive=True):
        emotion = get_emotion_from_filename(os.path.basename(fpath))
        if emotion not in OBSERVED_EMOTIONS:
            continue
        try:
            x.append(extract_feature(fpath))
            y.append(emotion)
        except Exception as e:
            logger.warning(f"Skipped {fpath}: {e}")

    X = np.array(x)
    _, x_test, _, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

    y_pred = model.predict(x_test)
    acc = accuracy_score(y_test, y_pred)

    logger.info(f"\nAccuracy: {acc*100:.2f}%\n")
    logger.info(classification_report(y_test, y_pred))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred, labels=OBSERVED_EMOTIONS)
    plt.figure(figsize=(7, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=OBSERVED_EMOTIONS,
        yticklabels=OBSERVED_EMOTIONS,
    )
    plt.title(f"Confusion Matrix  (Accuracy: {acc*100:.1f}%)")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    out = "models/confusion_matrix.png"
    plt.savefig(out, dpi=150)
    logger.info(f"Saved → {out}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-path", default="data/raw")
    parser.add_argument("--model-path", default="models/ser_model.pkl")
    args = parser.parse_args()
    evaluate(args.data_path, args.model_path)