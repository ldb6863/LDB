# -*- coding: utf-8 -*-
"""
verify_weights.py (v2 — 성별별 모델 둘 다 검증)
==================================================
train_faceshape.py로 만든 faceshape_weights_men.npz / faceshape_weights_women.npz가
실제로 core/cnn_classifier.py의 load_model()/predict_face_shape()로 제대로
로드되는지 Jetson으로 옮기기 전에 PC에서 먼저 확인하는 스크립트.

이게 필요한 이유: 학습은 새로 만든 모델 객체로 하고, 실제 서비스는 가중치만
꺼내서 "따로 조립한" 모델에 넣는 방식이라, 두 모델의 레이어 구성이 한 군데라도
어긋나면 set_weights()에서 에러가 나거나(운 좋은 경우) 조용히 엉뚱한 예측이
나올 수 있습니다(운 나쁜 경우). 반드시 학습 직후 이 스크립트로 확인하세요.

실행 위치: faceshape_project/training/ 안에서 실행
(dataset_faceshape_men.npz, dataset_faceshape_women.npz,
 faceshape_weights_men.npz, faceshape_weights_women.npz 가 같은 폴더에 있어야 함)
"""

import sys
import os
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import cnn_classifier

NUM_SAMPLES_TO_CHECK = 10


def check_gender(gender):
    print(f"\n{'='*50}\n  [{gender}] 테스트셋 샘플로 예측 확인\n{'='*50}")
    dataset_path = f"dataset_faceshape_{gender}.npz"
    if not os.path.isfile(dataset_path):
        print(f"[건너뜀] {dataset_path} 없음")
        return

    data = np.load(dataset_path)
    x_test, y_test = data["x_test"], data["y_test"]

    correct = 0
    n = min(NUM_SAMPLES_TO_CHECK, len(x_test))
    idxs = np.random.choice(len(x_test), n, replace=False)

    for i in idxs:
        img_rgb_uint8 = x_test[i].astype("uint8")
        img_bgr = cv2.cvtColor(img_rgb_uint8, cv2.COLOR_RGB2BGR)

        pred_shape, confidence = cnn_classifier.predict_face_shape(img_bgr, gender)
        true_shape = cnn_classifier.FACE_SHAPE_CLASSES[int(y_test[i])]

        mark = "O" if pred_shape == true_shape else "X"
        if pred_shape == true_shape:
            correct += 1
        print(f"  [{mark}] 정답: {true_shape:8s} / 예측: {pred_shape:8s} ({confidence:.1f}%)")

    print(f"\n[{gender}] 샘플 {n}개 중 {correct}개 정답 ({correct/n*100:.0f}%)")


def main():
    print("=== 1. 가중치 로드 시도 (men + women 둘 다) ===")
    try:
        cnn_classifier.load_model(".", transfer=True)
    except Exception as e:
        print(f"\n[실패] 가중치 로드 중 에러 발생: {e}")
        print("→ cnn_classifier.build_transfer_model()의 레이어 구성이")
        print("  train_faceshape.py와 정확히 같은지 확인하세요.")
        print("→ faceshape_weights_men.npz / faceshape_weights_women.npz 둘 다")
        print("  이 폴더에 있는지도 확인하세요.")
        return
    print("[성공] 가중치 로드 완료.\n")

    print("=== 2. 성별별 테스트셋 샘플로 예측 확인 ===")
    check_gender("men")
    check_gender("women")

    print("\n※ 이 스크립트는 '가중치가 제대로 들어갔는지' 배관 확인용입니다.")
    print("  전체 정확도는 train_faceshape.py 학습 로그의 classification_report를 참고하세요.")


if __name__ == "__main__":
    main()
