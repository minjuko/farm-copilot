"""Small dependency-free classification metrics for the Colab pipeline."""

from __future__ import annotations

from typing import Iterable


def classification_metrics(
    y_true: Iterable[int], y_pred: Iterable[int], class_ids: list[int]
) -> dict:
    truth, predicted = list(y_true), list(y_pred)
    if len(truth) != len(predicted) or not truth:
        raise ValueError('ground truth and predictions must have equal non-zero length')
    if any(value not in class_ids for value in truth + predicted):
        raise ValueError('class id outside configured class map')
    index = {class_id: position for position, class_id in enumerate(class_ids)}
    matrix = [[0 for _ in class_ids] for _ in class_ids]
    for actual, guess in zip(truth, predicted):
        matrix[index[actual]][index[guess]] += 1
    per_class = {}
    f1_values = []
    for class_id in class_ids:
        i = index[class_id]
        tp = matrix[i][i]
        support = sum(matrix[i])
        predicted_count = sum(row[i] for row in matrix)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[str(class_id)] = {
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'support': support,
        }
        f1_values.append(f1)
    healthy_id = next((class_id for class_id in class_ids if class_id == 0), None)
    healthy = per_class[str(healthy_id)] if healthy_id is not None else None
    return {
        'n': len(truth),
        'accuracy': sum(matrix[i][i] for i in range(len(class_ids))) / len(truth),
        'macro_f1': sum(f1_values) / len(f1_values),
        'per_class': per_class,
        'confusion_matrix': matrix,
        'normal_false_positive_rate': (
            1.0 - healthy['recall'] if healthy and healthy['support'] else None
        ),
    }
