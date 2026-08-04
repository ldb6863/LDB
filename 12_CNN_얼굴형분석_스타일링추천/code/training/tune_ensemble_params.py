# -*- coding: utf-8 -*-
"""
tune_ensemble_params.py   [CSV 재활용, TF/mediapipe 둘 다 필요 없음]
================================================================
CONFIDENCE_GAP_THRESHOLD와 LANDMARK_WEIGHT 여러 조합을 자동으로 다 시도해서
어느 조합이 제일 정확도가 높은지 찾습니다. eval_cnn_probs.py, eval_landmark_scores.py로
이미 만들어둔 CSV를 재사용하는 거라 순식간에 끝납니다 (CNN/mediapipe 재계산 없음).

combine_ensemble_results.py랑 같은 폴더에서 실행하세요.
"""

import pandas as pd
import itertools

CLASSES = ["Oval", "Rectangle", "Round", "Square"]

# 시도해볼 조합들 — 필요하면 범위 더 넓히거나 좁혀도 됨
GAP_THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
LANDMARK_WEIGHTS = [0.15, 0.25, 0.35, 0.45, 0.55, 0.65]


def load_merged(gender):
    cnn_df = pd.read_csv(f"cnn_probs_{gender}.csv")
    land_df = pd.read_csv(f"landmark_scores_{gender}.csv")
    cnn_df = cnn_df.rename(columns={c: f"{c}_cnn" for c in CLASSES})
    land_df = land_df.rename(columns={c: f"{c}_geo" for c in CLASSES})
    return cnn_df.merge(land_df, on="index", how="inner")


def evaluate(merged, gap_threshold, landmark_weight):
    n = len(merged)
    ensemble_correct = 0
    for _, row in merged.iterrows():
        true_label = row["true_label"]
        cnn_probs = {c: row[f"{c}_cnn"] for c in CLASSES}
        sorted_probs = sorted(cnn_probs.values(), reverse=True)
        gap = sorted_probs[0] - sorted_probs[1]
        cnn_pred = max(cnn_probs, key=cnn_probs.get)

        if gap >= gap_threshold or not row.get("detected", False):
            pred = cnn_pred
        else:
            geo_probs = {c: row[f"{c}_geo"] for c in CLASSES}
            combined = {
                c: (1 - landmark_weight) * cnn_probs[c] + landmark_weight * geo_probs[c]
                for c in CLASSES
            }
            pred = max(combined, key=combined.get)

        if pred == true_label:
            ensemble_correct += 1
    return ensemble_correct / n * 100


def main():
    for gender in ("men", "women"):
        try:
            merged = load_merged(gender)
        except FileNotFoundError as e:
            print(f"[건너뜀] {gender}: {e}")
            continue

        # CNN 단독 기준선
        cnn_correct = sum(
            max({c: row[f"{c}_cnn"] for c in CLASSES}, key=lambda c: row[f"{c}_cnn"]) == row["true_label"]
            for _, row in merged.iterrows()
        )
        cnn_baseline = cnn_correct / len(merged) * 100

        print(f"\n=== [{gender}] CNN 단독 기준선: {cnn_baseline:.1f}% ===")
        print(f"{'gap_thresh':>10} {'landmark_w':>10} {'accuracy':>10} {'vs baseline':>12}")

        results = []
        for gap_th, lw in itertools.product(GAP_THRESHOLDS, LANDMARK_WEIGHTS):
            acc = evaluate(merged, gap_th, lw)
            results.append((gap_th, lw, acc))

        results.sort(key=lambda r: -r[2])
        for gap_th, lw, acc in results[:10]:  # 상위 10개 조합만 출력
            print(f"{gap_th:>10.2f} {lw:>10.2f} {acc:>9.1f}% {acc - cnn_baseline:>+11.1f}%p")

        best_gap, best_lw, best_acc = results[0]
        print(f"\n최적 조합: CONFIDENCE_GAP_THRESHOLD={best_gap}, LANDMARK_WEIGHT={best_lw} "
              f"-> {best_acc:.1f}% ({best_acc - cnn_baseline:+.1f}%p)")


if __name__ == "__main__":
    main()
