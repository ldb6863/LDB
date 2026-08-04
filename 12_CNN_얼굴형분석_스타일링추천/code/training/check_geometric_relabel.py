# -*- coding: utf-8 -*-
"""
check_geometric_relabel.py
=============================
학습 데이터 전체(men+women)에 Farkas 안면계측학 기준 규칙(core.landmark_analyzer.
classify_by_geometry)을 적용해서, 원본 데이터셋 라벨과 얼마나 일치/불일치하는지
확인합니다. mediapipe만 필요합니다 (TensorFlow 불필요 — landmark_env에서 실행).

이 결과가 중요한 이유: "원본 라벨이 진짜 문제였는지"를 제 주관이 아니라
외부 학술 기준으로 확인하는 거라 지금까지 중 제일 객관적인 검증입니다.

실행 위치: men/, women/ 폴더와 같은 위치
"""

import glob
import os
import cv2
from collections import Counter

from core import landmark_analyzer as la

CLASS_NAMES = ["Oval", "Rectangle", "Round", "Square"]
SOURCE_ROOTS = {"men": r".\men", "women": r".\women"}


def process_folder(folder_path, gender, original_label, rows):
    files = (
        glob.glob(os.path.join(folder_path, "*.jpg")) +
        glob.glob(os.path.join(folder_path, "*.jpeg")) +
        glob.glob(os.path.join(folder_path, "*.png"))
    )
    ok, no_face = 0, 0
    for fp in files:
        img = cv2.imread(fp)
        if img is None:
            continue
        _, landmarks = la.detect_face_and_landmarks(img)
        if landmarks is None:
            no_face += 1
            continue
        metrics = la.extract_face_metrics(landmarks)
        geo_shape, _ = la.classify_by_geometry(metrics)
        if geo_shape is None:
            no_face += 1
            continue
        rows.append({"gender": gender, "original": original_label, "geometric": geo_shape})
        ok += 1
    print(f"  [{gender}/{original_label}] {ok}장 처리, {no_face}장 얼굴/계산 실패")


def main():
    rows = []
    for gender, root in SOURCE_ROOTS.items():
        if not os.path.isdir(root):
            print(f"경고: {root} 없음, 건너뜀")
            continue
        print(f"\n=== {gender} ===")
        for entry in sorted(os.listdir(root)):
            entry_path = os.path.join(root, entry)
            if not os.path.isdir(entry_path):
                continue
            matched = next((c for c in CLASS_NAMES if c.lower() == entry.lower()), None)
            if matched is None:
                continue
            process_folder(entry_path, gender, matched, rows)

    total = len(rows)
    agree = sum(1 for r in rows if r["original"] == r["geometric"])
    print(f"\n{'='*60}")
    print(f" 전체 {total}장 중 원본 라벨과 기하학적 판정 일치: {agree}장 ({agree/total*100:.1f}%)")
    print(f"{'='*60}")

    print("\n--- 원본 라벨별 기하학적 판정 분포 (혼동행렬 느낌) ---")
    for orig in CLASS_NAMES:
        subset = [r["geometric"] for r in rows if r["original"] == orig]
        if not subset:
            continue
        cnt = Counter(subset)
        total_o = len(subset)
        dist_str = ", ".join(f"{k}:{v}({v/total_o*100:.0f}%)" for k, v in cnt.most_common())
        print(f"  원본={orig:10s} (n={total_o:4d}) -> {dist_str}")

    print("\n※ 일치율이 낮을수록 '원본 라벨과 학술 기준이 많이 다르다'는 뜻입니다.")
    print("  단, 이 기하학적 규칙 자체도 완벽하지 않을 수 있으니 참고 자료로 보세요.")


if __name__ == "__main__":
    main()
