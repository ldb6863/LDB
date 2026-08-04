# -*- coding: utf-8 -*-
"""
eval_landmark_scores.py   [2단계 — landmark_env(mediapipe) 환경에서 실행]
================================================================
랜드마크 기하학적 점수만 계산해서 CSV로 저장합니다. TensorFlow는 전혀 안 씁니다
(core.landmark_analyzer만 불러오고 core.cnn_classifier는 임포트 안 함) —
그래서 mediapipe 전용 환경(landmark_env) 그대로 실행해도 protobuf 충돌이 안 납니다.

출력: landmark_scores_men.csv, landmark_scores_women.csv
"""

import sys
import os
import csv
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import landmark_analyzer as la

CLASSES = ["Oval", "Rectangle", "Round", "Square"]


def main():
    for gender in ("men", "women"):
        dataset_path = f"dataset_faceshape_{gender}.npz"
        if not os.path.isfile(dataset_path):
            print(f"[건너뜀] {dataset_path} 없음")
            continue

        data = np.load(dataset_path)
        x_test = data["x_test"]
        n = len(x_test)
        print(f"\n=== [{gender}] 랜드마크 점수 계산 중 ({n}장) ===")

        rows = []
        fail_count = 0
        for i in range(n):
            img_bgr = cv2.cvtColor(x_test[i].astype("uint8"), cv2.COLOR_RGB2BGR)
            _, landmarks = la.detect_face_and_landmarks(img_bgr)

            row = {"index": i, "detected": False}
            for c in CLASSES:
                row[c] = ""  # 검출 실패 시 빈 값

            if landmarks is not None:
                metrics = la.extract_face_metrics(landmarks)
                geo = la.geometric_class_scores(metrics, gender) if metrics else None
                if geo is not None:
                    row["detected"] = True
                    row.update(geo)
                else:
                    fail_count += 1
            else:
                fail_count += 1

            rows.append(row)
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{n}")

        out_path = f"landmark_scores_{gender}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["index", "detected"] + CLASSES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"저장 완료: {out_path} (검출 실패 {fail_count}/{n}장)")


if __name__ == "__main__":
    main()
