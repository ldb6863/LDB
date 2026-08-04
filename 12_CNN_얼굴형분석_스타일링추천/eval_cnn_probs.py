# -*- coding: utf-8 -*-
"""
eval_cnn_probs.py   [1단계 — dl2(TensorFlow) 환경에서 실행]
================================================================
CNN 확률 분포만 계산해서 CSV로 저장합니다. mediapipe는 전혀 안 씁니다
(core.cnn_classifier만 불러오고 core.landmark_analyzer는 임포트 안 함) —
그래서 dl2(TensorFlow 학습 환경) 그대로 실행해도 protobuf 충돌이 안 납니다.

출력: cnn_probs_men.csv, cnn_probs_women.csv
"""

import sys
import os
import csv
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import cnn_classifier

CLASSES = cnn_classifier.FACE_SHAPE_CLASSES


def main():
    cnn_classifier.load_model(".", transfer=True)

    for gender in ("men", "women"):
        dataset_path = f"dataset_faceshape_{gender}.npz"
        if not os.path.isfile(dataset_path):
            print(f"[건너뜀] {dataset_path} 없음")
            continue

        data = np.load(dataset_path)
        x_test, y_test = data["x_test"], data["y_test"]
        n = len(x_test)
        print(f"\n=== [{gender}] CNN 확률 계산 중 ({n}장) ===")

        rows = []
        for i in range(n):
            img_bgr = cv2.cvtColor(x_test[i].astype("uint8"), cv2.COLOR_RGB2BGR)
            probs = cnn_classifier.predict_proba(img_bgr, gender, use_tta=True)
            row = {"index": i, "true_label": CLASSES[int(y_test[i])]}
            row.update(probs)
            rows.append(row)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{n}")

        out_path = f"cnn_probs_{gender}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["index", "true_label"] + CLASSES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"저장 완료: {out_path}")


if __name__ == "__main__":
    main()
