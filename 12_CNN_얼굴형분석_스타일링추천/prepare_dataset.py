# -*- coding: utf-8 -*-
"""
prepare_dataset.py (v5 — 성별별 모델 분리)
=============================================
남성/여성 데이터를 하나로 합치지 않고, **각각 별도의 npz**로 저장합니다.
(성별별로 얼굴형 특징이 다르게 나타나서, 모델도 성별별로 따로 학습하기로 결정함)

폴더 구조 (train/test 미리 안 나뉘어 있음, 이 스크립트가 직접 나눔):

    men/
    ├── Oval/*.jpg
    ├── Rectangle/*.jpg
    ├── Round/*.jpg
    └── Square/*.jpg

    women/
    ├── Oval/*.jpg
    ├── Rectangle/*.jpg
    ├── Round/*.jpg
    └── Square/*.jpg

출력:
    dataset_faceshape_men.npz
    dataset_faceshape_women.npz
"""

import numpy as np
import glob
import os
from tensorflow.keras.preprocessing import image
from sklearn.model_selection import train_test_split

VER, HOR = 224, 224

# 라벨 순서: Oval(0) / Rectangle(1) / Round(2) / Square(3)
# core/cnn_classifier.py의 FACE_SHAPE_CLASSES와 반드시 동일해야 함
CLASS_NAMES = ["Oval", "Rectangle", "Round", "Square"]

TEST_SIZE = 0.2   # 전체의 20%를 테스트셋으로 분리

# 성별별 소스 경로 — 실제 경로로 바꾸세요
SOURCES = {
    "men": r".\men",
    "women": r".\women",
}


def load_folder_images(folder_path):
    files = sorted(
        glob.glob(os.path.join(folder_path, "*.jpg")) +
        glob.glob(os.path.join(folder_path, "*.jpeg")) +
        glob.glob(os.path.join(folder_path, "*.png"))
    )
    X = []
    skipped = []
    for filepath in files:
        try:
            img = image.load_img(filepath, color_mode="rgb", target_size=(VER, HOR))
            X.append(np.array(img, dtype=np.uint8))  # uint8로 저장 (메모리 절약)
        except Exception as e:
            skipped.append((filepath, str(e)))
    if skipped:
        print(f"    [경고] 손상되어 건너뛴 파일 {len(skipped)}개:")
        for filepath, err in skipped:
            print(f"      - {filepath} ({err})")
    return np.array(X, dtype=np.uint8) if X else np.empty((0, VER, HOR, 3), dtype=np.uint8)


def build_dataset_for(root):
    X_list, y_list = [], []
    for entry in sorted(os.listdir(root)):
        entry_path = os.path.join(root, entry)
        if not os.path.isdir(entry_path):
            continue
        matched = next((c for c in CLASS_NAMES if c.lower() == entry.lower()), None)
        if matched is None:
            print(f"  [건너뜀] {entry_path} (CLASS_NAMES에 없는 폴더)")
            continue
        X = load_folder_images(entry_path)
        label = CLASS_NAMES.index(matched)
        print(f"  {entry_path} -> {matched}({label}) : {len(X)}장")
        X_list.append(X)
        y_list.append(label * np.ones(len(X)))

    X_all = np.concatenate(X_list, axis=0)
    y_all = np.concatenate(y_list, axis=0)
    return X_all, y_all


def main():
    for gender, root in SOURCES.items():
        if not os.path.isdir(root):
            print(f"경고: {root} 폴더가 없습니다. {gender} 건너뜁니다.")
            continue

        print(f"\n=== [{gender}] 로드 중 ===")
        X_all, y_all = build_dataset_for(root)
        print(f"[{gender}] 전체 이미지: {X_all.shape[0]}장")

        x_train, x_test, y_train, y_test = train_test_split(
            X_all, y_all, test_size=TEST_SIZE, random_state=0, stratify=y_all
        )

        print(f"[{gender}] 학습셋: {len(x_train)}장 / 테스트셋: {len(x_test)}장")
        for i, name in enumerate(CLASS_NAMES):
            print(f"    {name}: 학습 {int((y_train==i).sum())}장 / 테스트 {int((y_test==i).sum())}장")

        output_path = f".\\dataset_faceshape_{gender}.npz"
        np.savez(output_path, x_train=x_train, x_test=x_test, y_train=y_train, y_test=y_test)
        print(f"[{gender}] 저장 완료: {output_path}")


if __name__ == "__main__":
    main()