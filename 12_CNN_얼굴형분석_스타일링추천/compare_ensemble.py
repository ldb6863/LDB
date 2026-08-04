# -*- coding: utf-8 -*-
"""
compare_ensemble.py
=====================
"CNN 단독"과 "CNN + 랜드마크 앙상블"의 정확도를 테스트셋 전체로 비교합니다.
1번 아이디어(CNN이 애매할 때 랜드마크로 타이브레이크)가 실제로 효과 있는지
직접 확인하는 스크립트입니다.

실행 위치: faceshape_project/training/ 안에서 실행
(dataset_faceshape_men.npz, dataset_faceshape_women.npz,
 faceshape_weights_men.npz, faceshape_weights_women.npz 가 있어야 함)

주의: 테스트셋 npz 이미지는 얼굴만 이미 잘라져 있는 상태라(CNN 학습용으로
crop된 이미지), landmark_analyzer로 다시 얼굴을 검출해야 합니다 — npz 이미지
자체가 이미 확대된 얼굴이라 원본 웹캠 프레임과는 배율이 달라서, 랜드마크
검출이 원본만큼 안정적이지 않을 수 있습니다(참고용 결과로 보시면 됩니다).
"""

import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import cnn_classifier, landmark_analyzer, ensemble

CONFIDENCE_GAP_THRESHOLD = 0.15
LANDMARK_WEIGHT = 0.35


def evaluate_gender(gender):
    dataset_path = f"dataset_faceshape_{gender}.npz"
    if not os.path.isfile(dataset_path):
        print(f"[건너뜀] {dataset_path} 없음")
        return

    data = np.load(dataset_path)
    x_test, y_test = data["x_test"], data["y_test"]

    cnn_correct = 0
    ensemble_correct = 0
    ensemble_used_count = 0
    ensemble_helped = 0    # CNN 틀렸는데 앙상블이 맞춘 경우
    ensemble_hurt = 0      # CNN 맞았는데 앙상블이 틀린 경우
    landmark_fail_count = 0

    n = len(x_test)
    print(f"\n=== [{gender}] 테스트셋 {n}장 평가 중 ===")

    for i in range(n):
        img_rgb_uint8 = x_test[i].astype("uint8")
        img_bgr = cv2.cvtColor(img_rgb_uint8, cv2.COLOR_RGB2BGR)
        true_shape = cnn_classifier.FACE_SHAPE_CLASSES[int(y_test[i])]

        # CNN 단독
        cnn_pred, _ = cnn_classifier.predict_face_shape(img_bgr, gender, use_tta=True)
        is_cnn_correct = (cnn_pred == true_shape)
        if is_cnn_correct:
            cnn_correct += 1

        # 앙상블 (랜드마크 검출 필요 — npz 이미지 자체에서 다시 검출)
        _, landmarks = landmark_analyzer.detect_face_and_landmarks(img_bgr)
        if landmarks is None:
            landmark_fail_count += 1
            ens_pred = cnn_pred  # 랜드마크 실패 시 CNN 결과 그대로
        else:
            ens_pred, _, method = ensemble.predict_face_shape_ensemble(
                img_bgr, landmarks, gender,
                confidence_gap_threshold=CONFIDENCE_GAP_THRESHOLD,
                landmark_weight=LANDMARK_WEIGHT,
            )
            if method == "ensemble":
                ensemble_used_count += 1

        is_ensemble_correct = (ens_pred == true_shape)
        if is_ensemble_correct:
            ensemble_correct += 1

        if not is_cnn_correct and is_ensemble_correct:
            ensemble_helped += 1
        if is_cnn_correct and not is_ensemble_correct:
            ensemble_hurt += 1

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{n} 처리 중...")

    cnn_acc = cnn_correct / n * 100
    ens_acc = ensemble_correct / n * 100

    print(f"\n--- [{gender}] 결과 ---")
    print(f"  CNN 단독 정확도:     {cnn_correct}/{n} = {cnn_acc:.1f}%")
    print(f"  앙상블 정확도:       {ensemble_correct}/{n} = {ens_acc:.1f}%")
    print(f"  차이:                {ens_acc - cnn_acc:+.1f}%p")
    print(f"  앙상블이 실제 개입한 케이스: {ensemble_used_count}/{n} "
          f"({ensemble_used_count/n*100:.0f}%, CNN이 애매해했던 경우)")
    print(f"  랜드마크 검출 실패:  {landmark_fail_count}/{n}")
    print(f"  앙상블 덕에 맞춘 경우: {ensemble_helped}건 / 앙상블 때문에 틀린 경우: {ensemble_hurt}건")


def main():
    print("=== 가중치 로드 ===")
    cnn_classifier.load_model(".", transfer=True)

    for gender in ("men", "women"):
        evaluate_gender(gender)


if __name__ == "__main__":
    main()
