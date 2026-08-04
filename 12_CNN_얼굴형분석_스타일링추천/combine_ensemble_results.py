# -*- coding: utf-8 -*-
"""
combine_ensemble_results.py   [3단계 — 아무 환경에서나 실행 가능, pandas만 있으면 됨]
================================================================
1단계(eval_cnn_probs.py)와 2단계(eval_landmark_scores.py)에서 만든 CSV 두 개를
합쳐서, CNN 단독 정확도 vs 앙상블 정확도를 비교합니다.
TensorFlow도 mediapipe도 필요 없어서 어느 환경(dl2든 landmark_env든 base든)
에서 돌려도 됩니다.

실행 전: cnn_probs_men.csv, cnn_probs_women.csv, landmark_scores_men.csv,
         landmark_scores_women.csv 네 파일이 다 한 폴더에 있어야 함
         (1단계, 2단계 결과를 같은 폴더로 모아두세요)
"""

import pandas as pd

CLASSES = ["Oval", "Rectangle", "Round", "Square"]
CONFIDENCE_GAP_THRESHOLD = 0.15
LANDMARK_WEIGHT = 0.35


def evaluate_gender(gender):
    cnn_path = f"cnn_probs_{gender}.csv"
    land_path = f"landmark_scores_{gender}.csv"

    try:
        cnn_df = pd.read_csv(cnn_path)
        land_df = pd.read_csv(land_path)
    except FileNotFoundError as e:
        print(f"[건너뜀] {gender}: {e}")
        return

    cnn_df = cnn_df.rename(columns={c: f"{c}_cnn" for c in CLASSES})
    land_df = land_df.rename(columns={c: f"{c}_geo" for c in CLASSES})
    merged = cnn_df.merge(land_df, on="index", how="inner")

    n = len(merged)
    cnn_correct = 0
    ensemble_correct = 0
    ensemble_used = 0
    helped, hurt = 0, 0

    for _, row in merged.iterrows():
        true_label = row["true_label"]
        cnn_probs = {c: row[f"{c}_cnn"] for c in CLASSES}

        sorted_probs = sorted(cnn_probs.values(), reverse=True)
        gap = sorted_probs[0] - sorted_probs[1]
        cnn_pred = max(cnn_probs, key=cnn_probs.get)
        is_cnn_correct = (cnn_pred == true_label)
        if is_cnn_correct:
            cnn_correct += 1

        if gap >= CONFIDENCE_GAP_THRESHOLD or not row.get("detected", False):
            ens_pred = cnn_pred
        else:
            geo_probs = {c: row[f"{c}_geo"] for c in CLASSES}
            combined = {
                c: (1 - LANDMARK_WEIGHT) * cnn_probs[c] + LANDMARK_WEIGHT * geo_probs[c]
                for c in CLASSES
            }
            ens_pred = max(combined, key=combined.get)
            ensemble_used += 1

        is_ens_correct = (ens_pred == true_label)
        if is_ens_correct:
            ensemble_correct += 1
        if not is_cnn_correct and is_ens_correct:
            helped += 1
        if is_cnn_correct and not is_ens_correct:
            hurt += 1

    cnn_acc = cnn_correct / n * 100
    ens_acc = ensemble_correct / n * 100

    print(f"\n=== [{gender}] 결과 (총 {n}장) ===")
    print(f"  CNN 단독 정확도: {cnn_correct}/{n} = {cnn_acc:.1f}%")
    print(f"  앙상블 정확도:   {ensemble_correct}/{n} = {ens_acc:.1f}%")
    print(f"  차이:            {ens_acc - cnn_acc:+.1f}%p")
    print(f"  앙상블 개입 비율: {ensemble_used}/{n} ({ensemble_used/n*100:.0f}%)")
    print(f"  앙상블 덕에 맞춘 경우: {helped}건 / 앙상블 때문에 틀린 경우: {hurt}건")


def main():
    for gender in ("men", "women"):
        evaluate_gender(gender)


if __name__ == "__main__":
    main()
