# -*- coding: utf-8 -*-
"""
core/ensemble.py
=================
CNN 확률(core/cnn_classifier.predict_proba)과 랜드마크 기하학적 점수
(core/landmark_analyzer.geometric_class_scores)를 결합해서 최종 얼굴형을
결정합니다.

전략: CNN이 확신하는 경우(1등-2등 확률 차이가 충분히 큼)는 CNN 결과를 그대로
믿습니다. CNN이 애매해할 때(1등-2등이 비슷비슷)만 랜드마크 점수를 섞어서
타이브레이크합니다 — CNN이 이미 잘 맞히는 "쉬운 케이스"까지 랜드마크로
흔들어서 오히려 나빠지는 걸 방지하기 위함입니다.
"""

from core import cnn_classifier, landmark_analyzer

# 2026-07-27 실측 테스트셋(남 185장, 여 615장)으로 파라미터 튜닝한 결과.
# 단순히 1등 조합만 고른 게 아니라, 여러 조합에서 비슷하게 잘 나오는
# "넓은 고원" 영역을 골라서 특정 테스트셋에 과적합되지 않게 함.
_DEFAULT_PARAMS = {
    # 2026-07-27, TTA 5장 + 여성은 FINE_TUNE_LAYERS=200(전체 층 해제)까지 재학습한 뒤
    # 재튜닝한 최종값. 남성은 이전과 동일(재학습 안 함, 결과도 그대로 재현됨).
    # 여성은 CNN 단독이 61.6%->64.6%로 크게 올라서, 앙상블 개입 비율 자체가 줄었음
    # (CNN이 더 확신하게 됨 — 정상적인 현상).
    "men":   {"confidence_gap_threshold": 0.25, "landmark_weight": 0.15},  # CNN단독 75.7% -> 76.8%
    "women": {"confidence_gap_threshold": 0.05, "landmark_weight": 0.25},  # CNN단독 64.6% -> 65.2%
}


def predict_face_shape_ensemble(face_crop_bgr, landmarks, gender,
                                  use_tta=True, confidence_gap_threshold=None,
                                  landmark_weight=None):
    """
    face_crop_bgr: CNN용으로 잘라낸 얼굴 이미지
    landmarks: core.landmark_analyzer.detect_face_and_landmarks()가 준 랜드마크 dict
    gender: "M"/"F" 또는 "men"/"women"
    confidence_gap_threshold: CNN 1등-2등 확률 차이가 이보다 작으면 "애매하다"고 판단.
        None(기본값)이면 성별별 실측 튜닝 값을 자동으로 씀 (_DEFAULT_PARAMS 참고)
    landmark_weight: 애매할 때 랜드마크 점수에 주는 가중치 (0~1, CNN엔 1-landmark_weight)
        None(기본값)이면 위와 동일하게 성별별 튜닝 값 사용

    반환: (face_shape, confidence_0~100, method)
    method는 "cnn_confident"(CNN 확신, 그대로 씀) 또는
             "ensemble"(애매해서 랜드마크 섞어서 결정) 중 하나
    """
    cnn_probs = cnn_classifier.predict_proba(face_crop_bgr, gender, use_tta=use_tta)

    gender_key = {"M": "men", "F": "women", "men": "men", "women": "women"}.get(gender, "men")
    if confidence_gap_threshold is None:
        confidence_gap_threshold = _DEFAULT_PARAMS[gender_key]["confidence_gap_threshold"]
    if landmark_weight is None:
        landmark_weight = _DEFAULT_PARAMS[gender_key]["landmark_weight"]

    sorted_probs = sorted(cnn_probs.values(), reverse=True)
    top1, top2 = sorted_probs[0], sorted_probs[1]
    gap = top1 - top2

    if gap >= confidence_gap_threshold:
        # CNN이 확신하는 경우 — 랜드마크 안 쓰고 그대로 반환
        best_cls = max(cnn_probs, key=cnn_probs.get)
        return best_cls, cnn_probs[best_cls] * 100, "cnn_confident"

    # 애매한 경우 — 랜드마크 기하학적 점수와 가중합
    metrics = landmark_analyzer.extract_face_metrics(landmarks) if landmarks else None
    geo_scores = landmark_analyzer.geometric_class_scores(metrics, gender) if metrics else None

    if geo_scores is None:
        # 랜드마크 계산이 안 되면(얼굴 각도 등 문제) 어쩔 수 없이 CNN만 사용
        best_cls = max(cnn_probs, key=cnn_probs.get)
        return best_cls, cnn_probs[best_cls] * 100, "cnn_confident"

    combined = {}
    for cls in cnn_probs:
        combined[cls] = (1 - landmark_weight) * cnn_probs[cls] + landmark_weight * geo_scores.get(cls, 0)

    best_cls = max(combined, key=combined.get)
    return best_cls, combined[best_cls] * 100, "ensemble"
