# # -*- coding: utf-8 -*-
# """
# train_faceshape.py (v2 — 성별별 모델)
# =======================================
# 수업 템플릿(2_1_train.전이학습_검증.py)을 얼굴형 4클래스용으로 개조한 버전.
# PC/Colab에서 실행 (Jetson에서 직접 학습하지 않음 — 기존 가위바위보 실습과 동일한 흐름).

# 성별별로 모델을 따로 학습합니다. 아래 GENDER 값을 "men" -> "women" 순으로 바꿔가며
# 이 스크립트를 두 번 실행하면 됩니다 (Spyder면 F5 두 번).

# 산출물 (GENDER에 따라 파일명 자동으로 달라짐):
#   - my_cnn_model_faceshape_{GENDER}.h5
#   - faceshape_weights_{GENDER}.npz   ← 이 두 파일(men/women 각각)을
#     faceshape_project/ 폴더에 넣으면 core/cnn_classifier.py가 둘 다 로드해서 씁니다.

# core/cnn_classifier.py의 build_transfer_model()과 레이어 구성이 정확히 같아야
# 가중치가 맞게 들어갑니다 (Sequential 순서: Rescaling → MobileNetV2 → GAP →
# Dense(128) → Dropout(0.4) → Dense(4, softmax)).
# """

# import warnings
# warnings.filterwarnings("ignore")

# import time
# import numpy as np
# import matplotlib.pyplot as plt
# import tensorflow as tf
# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
# from tensorflow.keras.applications import MobileNetV2
# from tensorflow.keras import utils
# from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
# from sklearn.metrics import classification_report, confusion_matrix

# # ------------------------------------------------------------------
# # ★ 이 값만 바꿔서 두 번 실행하세요: "men" 한 번, "women" 한 번
# # ------------------------------------------------------------------
# GENDER = "women"   # "men" 또는 "women"

# VER, HOR = 224, 224
# NUM_CLASSES = 4
# CLASS_NAMES = ["Oval", "Rectangle", "Round", "Square"]  # prepare_dataset.py와 순서 동일해야 함

# DATASET_NPZ = f".\\dataset_faceshape_{GENDER}.npz"  # prepare_dataset.py의 출력 파일명과 동일

# # ------------------------------------------------------------------
# # 1. 데이터셋 불러오기
# # ------------------------------------------------------------------
# print(f"\n{'='*50}\n  GENDER = {GENDER}\n{'='*50}")

# data = np.load(DATASET_NPZ)
# x_train, x_test = data["x_train"], data["x_test"]
# y_train, y_test = data["y_train"], data["y_test"]

# print(f"학습셋: {x_train.shape[0]}장 / 테스트셋: {x_test.shape[0]}장")

# # 주의: 여기서 x_train 전체를 float32로 미리 바꾸지 않습니다.
# # (3299장 전체를 한 번에 float32로 만들면 1.85GB가 필요해서 MemoryError 발생)
# # 대신 모델 맨 앞에 Rescaling(1/255) 레이어를 넣어서, 학습 중 배치 단위(16장씩)로만
# # 변환되게 합니다 — 한 번에 필요한 메모리가 수 MB 수준으로 줄어듭니다.

# y_train_encoded = utils.to_categorical(y_train, num_classes=NUM_CLASSES)
# y_test_encoded = utils.to_categorical(y_test, num_classes=NUM_CLASSES)

# # ------------------------------------------------------------------
# # 2. MobileNetV2 기반 전이학습 모델
# #    ※ core.py의 build_transfer_model()과 "가중치를 가진 레이어" 구성이 동일해야 함.
# #      Rescaling/증강 레이어는 가중치가 없어서 get_weights()에 안 잡히므로,
# #      core.py 쪽에 그대로 안 넣어도(=추론 때는 최소 구성만 있어도) 괜찮습니다.
# #      단, core.py의 predict_face_shape()도 "미리 /255 하지 않고" 이 레이어가
# #      대신 나누도록 맞춰뒀습니다 — 이중으로 나누면 안 되니 주의하세요.
# # ------------------------------------------------------------------
# from tensorflow.keras.layers import RandomFlip, RandomRotation, RandomZoom, RandomContrast, Rescaling

# data_augmentation = Sequential([
#     RandomFlip("horizontal"),
#     RandomRotation(0.05),      # 약 ±18도
#     RandomZoom(0.1),
#     RandomContrast(0.1),
# ], name="augmentation")

# base_model = MobileNetV2(weights="imagenet", include_top=False, input_shape=(VER, HOR, 3))
# base_model.trainable = False  # 1차: 사전학습 가중치 고정 (특징 추출기로만 사용)

# model = Sequential([
#     Rescaling(1.0 / 255, input_shape=(VER, HOR, 3)),  # 0~255 -> 0~1, 배치 단위로 변환
#     data_augmentation,   # 학습(training=True)할 때만 작동, 추론 때는 자동으로 통과됨
#     base_model,
#     GlobalAveragePooling2D(),
#     Dense(128, activation="relu"),
#     Dropout(0.4),
#     Dense(NUM_CLASSES, activation="softmax"),
# ])
# model.summary()

# model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["acc"])

# # ------------------------------------------------------------------
# # 3. 학습
# # ------------------------------------------------------------------
# early_stopping = EarlyStopping(monitor="val_loss", patience=5, verbose=1, restore_best_weights=True)
# checkpoint = ModelCheckpoint(
#     filepath=f"my_cnn_model_faceshape_{GENDER}.h5", monitor="val_loss", save_best_only=True, verbose=1
# )


# class TimeHistory(tf.keras.callbacks.Callback):
#     def on_train_begin(self, logs=None):
#         self.start = time.time()
#         print("\n=== 학습 시작 ===")

#     def on_train_end(self, logs=None):
#         elapsed = time.time() - self.start
#         print(f"\n총 학습 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")


# history = model.fit(
#     x_train, y_train_encoded,
#     epochs=50,
#     batch_size=16,
#     validation_data=(x_test, y_test_encoded),
#     callbacks=[early_stopping, checkpoint, TimeHistory()],
# )

# # ------------------------------------------------------------------
# # 3-1. 미세조정 (Fine-tuning) — MobileNetV2 상위 일부 층을 풀어서 추가 학습
# #    1차(freeze) 학습은 "일반 사물" 특징만 재사용하는 수준이라, 여기서 상위 층 일부를
# #    아주 낮은 학습률로 살짝 더 학습시켜 얼굴형처럼 미세한 차이를 더 잘 잡게 합니다.
# #    시간이 부족하면 FINE_TUNE = False 로 끄고 1차 결과만 써도 됩니다.
# # ------------------------------------------------------------------
# FINE_TUNE = True
# FINE_TUNE_LAYERS = 30  # base_model 맨 위 30개 층만 풀기 (나머지는 계속 freeze)

# if FINE_TUNE:
#     print("\n" + "=" * 50)
#     print(" 미세조정(fine-tuning) 시작")
#     print("=" * 50)

#     base_model.trainable = True
#     for layer in base_model.layers[:-FINE_TUNE_LAYERS]:
#         layer.trainable = False  # 상위 일부 층만 남기고 나머지는 계속 고정

#     # BatchNormalization 층은 상위 30개 안에 있어도 계속 얼려둠.
#     # (작은 배치·적은 데이터로 BatchNorm 통계까지 같이 흔들면 학습이 불안정해져서
#     #  fine-tune 시작 지점에 loss가 확 튀는 현상이 생김 — 이걸 막는 표준적인 방법)
#     for layer in base_model.layers:
#         if isinstance(layer, tf.keras.layers.BatchNormalization):
#             layer.trainable = False

#     # 학습률을 아주 낮게 — 이미 학습된 특징이 크게 망가지지 않도록
#     model.compile(
#         optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
#         loss="categorical_crossentropy",
#         metrics=["acc"],
#     )

#     fine_tune_early_stopping = EarlyStopping(
#         monitor="val_loss", patience=6, verbose=1, restore_best_weights=True
#     )
#     fine_tune_checkpoint = ModelCheckpoint(
#         filepath=f"my_cnn_model_faceshape_{GENDER}_finetuned.h5",
#         monitor="val_loss", save_best_only=True, verbose=1,
#     )
#     reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
#         monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7, verbose=1
#     )

#     history_ft = model.fit(
#         x_train, y_train_encoded,
#         epochs=30,
#         batch_size=16,
#         validation_data=(x_test, y_test_encoded),
#         callbacks=[fine_tune_early_stopping, fine_tune_checkpoint, reduce_lr],
#     )

# # ------------------------------------------------------------------
# # 4. 평가
# # ------------------------------------------------------------------
# test_loss, test_acc = model.evaluate(x_test, y_test_encoded, verbose=0)
# print(f"\nFinal Best Test Accuracy: {test_acc:.4f}")

# y_pred = model.predict(x_test, verbose=0)
# y_pred_classes = np.argmax(y_pred, axis=1)

# print("\n[상세 분류 성능 리포트]")
# print(classification_report(y_test, y_pred_classes, target_names=CLASS_NAMES))
# print("[혼동 행렬]")
# print(confusion_matrix(y_test, y_pred_classes))

# # 학습 곡선 (미세조정을 했으면 이어붙여서 하나의 그래프로 표시)
# if FINE_TUNE:
#     acc = history.history["acc"] + history_ft.history["acc"]
#     val_acc = history.history["val_acc"] + history_ft.history["val_acc"]
#     loss = history.history["loss"] + history_ft.history["loss"]
#     val_loss = history.history["val_loss"] + history_ft.history["val_loss"]
#     fine_tune_start_epoch = len(history.history["acc"])
# else:
#     acc = history.history["acc"]
#     val_acc = history.history["val_acc"]
#     loss = history.history["loss"]
#     val_loss = history.history["val_loss"]
#     fine_tune_start_epoch = None

# plt.figure(figsize=(12, 5))
# plt.subplot(1, 2, 1)
# plt.plot(acc, label="Train Accuracy", marker="o")
# plt.plot(val_acc, label="Validation Accuracy", marker="x")
# if fine_tune_start_epoch:
#     plt.axvline(fine_tune_start_epoch - 0.5, color="gray", linestyle="--", label="Fine-tune 시작")
# plt.title("Model Accuracy"); plt.xlabel("Epoch"); plt.ylabel("Accuracy"); plt.legend(); plt.grid(True)
# plt.subplot(1, 2, 2)
# plt.plot(loss, label="Train Loss", marker="o")
# plt.plot(val_loss, label="Validation Loss", marker="x")
# if fine_tune_start_epoch:
#     plt.axvline(fine_tune_start_epoch - 0.5, color="gray", linestyle="--", label="Fine-tune 시작")
# plt.title("Model Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss"); plt.legend(); plt.grid(True)
# plt.tight_layout()
# plt.savefig(f"training_curve_{GENDER}.png")
# print(f"학습 곡선을 training_curve_{GENDER}.png로 저장했습니다.")

# # ------------------------------------------------------------------
# # 5. Jetson 이식용 가중치 추출 (핵심 — 이걸 빼먹으면 Jetson에서 못 씀)
# # ------------------------------------------------------------------
# weights = model.get_weights()
# np.savez(f"faceshape_weights_{GENDER}.npz", *weights)
# print(f"\nJetson 이식용 가중치 저장 완료: faceshape_weights_{GENDER}.npz ({len(weights)}개 배열)")
# print(f"이 파일을 faceshape_project/ 폴더의 faceshape_weights_{GENDER}.npz 자리에 넣으면 됩니다.")
# print("men, women 둘 다 끝났으면 GENDER를 바꿔서 반대쪽도 실행하세요 (아직 안 했다면).")

# -*- coding: utf-8 -*-
"""
train_faceshape.py (v2 — 성별별 모델)
=======================================
수업 템플릿(2_1_train.전이학습_검증.py)을 얼굴형 4클래스용으로 개조한 버전.
PC/Colab에서 실행 (Jetson에서 직접 학습하지 않음 — 기존 가위바위보 실습과 동일한 흐름).

성별별로 모델을 따로 학습합니다. 아래 GENDER 값을 "men" -> "women" 순으로 바꿔가며
이 스크립트를 두 번 실행하면 됩니다 (Spyder면 F5 두 번).

산출물 (GENDER에 따라 파일명 자동으로 달라짐):
  - my_cnn_model_faceshape_{GENDER}.h5
  - faceshape_weights_{GENDER}.npz   ← 이 두 파일(men/women 각각)을
    faceshape_project/ 폴더에 넣으면 core/cnn_classifier.py가 둘 다 로드해서 씁니다.

core/cnn_classifier.py의 build_transfer_model()과 레이어 구성이 정확히 같아야
가중치가 맞게 들어갑니다 (Sequential 순서: Rescaling → MobileNetV2 → GAP →
Dense(128) → Dropout(0.4) → Dense(4, softmax)).
"""

import warnings
warnings.filterwarnings("ignore")

import time
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras import utils
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.metrics import classification_report, confusion_matrix

# ------------------------------------------------------------------
# ★ 이 값만 바꿔서 두 번 실행하세요: "men" 한 번, "women" 한 번
# ------------------------------------------------------------------
GENDER = "women"   # "men" 또는 "women"

# 성별별 하이퍼파라미터 — 남성(30, 일반 loss)은 이미 75.7%(앙상블 포함) 잘 나와서
# 그대로 유지. 여성은 데이터가 4배 많아서(3,200장) 더 많은 층을 풀어도 될 것
# 같아서 FINE_TUNE_LAYERS를 늘리고, Oval이 유독 헷갈리는 문제에 맞춰 Focal Loss로 교체.
_GENDER_CONFIG = {
    "men":   {"fine_tune_layers": 30, "use_focal_loss": False, "use_mixup": False},
    "women": {"fine_tune_layers": 200, "use_focal_loss": True, "use_mixup": True},
}
_cfg = _GENDER_CONFIG[GENDER]

VER, HOR = 224, 224
NUM_CLASSES = 4
CLASS_NAMES = ["Oval", "Rectangle", "Round", "Square"]  # prepare_dataset.py와 순서 동일해야 함

DATASET_NPZ = f".\\dataset_faceshape_{GENDER}.npz"  # prepare_dataset.py의 출력 파일명과 동일


def focal_loss(gamma=2.0, alpha=0.25):
    """Focal Loss — 잘 맞히는 쉬운 샘플의 loss 기여를 줄이고, 헷갈리는(예측 확률이
    낮은) 샘플에 학습이 더 집중되게 함. 클래스 불균형/난이도 불균형에 자주 쓰임.
    gamma가 클수록 "어려운 샘플 집중"이 강해짐 (2.0이 논문 기본값)."""
    cce = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1, reduction="none")

    def loss_fn(y_true, y_pred):
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1 - 1e-7)
        ce = cce(y_true, y_pred)
        p_t = tf.reduce_sum(y_true * y_pred, axis=-1)
        modulating_factor = tf.pow(1.0 - p_t, gamma)
        return alpha * modulating_factor * ce

    return loss_fn


# ------------------------------------------------------------------
# 1. 데이터셋 불러오기
# ------------------------------------------------------------------
print(f"\n{'='*50}\n  GENDER = {GENDER} | FINE_TUNE_LAYERS = {_cfg['fine_tune_layers']} | "
      f"focal_loss = {_cfg['use_focal_loss']} | mixup = {_cfg['use_mixup']}\n{'='*50}")

data = np.load(DATASET_NPZ)
x_train, x_test = data["x_train"], data["x_test"]
y_train, y_test = data["y_train"], data["y_test"]

print(f"학습셋: {x_train.shape[0]}장 / 테스트셋: {x_test.shape[0]}장")

# 주의: 여기서 x_train 전체를 float32로 미리 바꾸지 않습니다.
# (3299장 전체를 한 번에 float32로 만들면 1.85GB가 필요해서 MemoryError 발생)
# 대신 모델 맨 앞에 Rescaling(1/255) 레이어를 넣어서, 학습 중 배치 단위(16장씩)로만
# 변환되게 합니다 — 한 번에 필요한 메모리가 수 MB 수준으로 줄어듭니다.

y_train_encoded = utils.to_categorical(y_train, num_classes=NUM_CLASSES)
y_test_encoded = utils.to_categorical(y_test, num_classes=NUM_CLASSES)

# ------------------------------------------------------------------
# 2. MobileNetV2 기반 전이학습 모델
#    ※ core.py의 build_transfer_model()과 "가중치를 가진 레이어" 구성이 동일해야 함.
#      Rescaling/증강 레이어는 가중치가 없어서 get_weights()에 안 잡히므로,
#      core.py 쪽에 그대로 안 넣어도(=추론 때는 최소 구성만 있어도) 괜찮습니다.
#      단, core.py의 predict_face_shape()도 "미리 /255 하지 않고" 이 레이어가
#      대신 나누도록 맞춰뒀습니다 — 이중으로 나누면 안 되니 주의하세요.
# ------------------------------------------------------------------
from tensorflow.keras.layers import RandomFlip, RandomRotation, RandomZoom, RandomContrast, Rescaling

data_augmentation = Sequential([
    RandomFlip("horizontal"),
    RandomRotation(0.05),      # 약 ±18도
    RandomZoom(0.1),
    RandomContrast(0.1),
], name="augmentation")

base_model = MobileNetV2(weights="imagenet", include_top=False, input_shape=(VER, HOR, 3))
base_model.trainable = False  # 1차: 사전학습 가중치 고정 (특징 추출기로만 사용)

from tensorflow.keras.regularizers import l2

model = Sequential([
    Rescaling(1.0 / 255, input_shape=(VER, HOR, 3)),  # 0~255 -> 0~1, 배치 단위로 변환
    data_augmentation,   # 학습(training=True)할 때만 작동, 추론 때는 자동으로 통과됨
    base_model,
    GlobalAveragePooling2D(),
    Dense(128, activation="relu", kernel_regularizer=l2(1e-4)),  # 약한 L2 규제로 과적합 억제
    Dropout(0.4),
    Dense(NUM_CLASSES, activation="softmax"),
])
model.summary()

# label_smoothing: 모델이 정답에 100% 확신하지 않도록 살짝 완화 (과적합 억제, 일반화 개선)
# _cfg["use_focal_loss"]가 True면(여성 기본값) Focal Loss, 아니면(남성 기본값) 기존 방식
if _cfg["use_focal_loss"]:
    loss_fn = focal_loss(gamma=2.0, alpha=0.25)
    print("[loss] Focal Loss 사용 (gamma=2.0, alpha=0.25)")
else:
    loss_fn = tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.1)
    print("[loss] 일반 CategoricalCrossentropy 사용")
model.compile(optimizer="adam", loss=loss_fn, metrics=["acc"])

# 클래스 가중치: 약한 클래스(Oval 등)에 학습 중 더 신경 쓰게 함
from sklearn.utils.class_weight import compute_class_weight
class_weights_arr = compute_class_weight("balanced", classes=np.arange(NUM_CLASSES), y=y_train)
class_weight_dict = {i: w for i, w in enumerate(class_weights_arr)}
print(f"\n클래스 가중치: {class_weight_dict}")

# ------------------------------------------------------------------
# 3. 학습
# ------------------------------------------------------------------
early_stopping = EarlyStopping(monitor="val_loss", patience=5, verbose=1, restore_best_weights=True)
checkpoint = ModelCheckpoint(
    filepath=f"my_cnn_model_faceshape_{GENDER}.h5", monitor="val_loss", save_best_only=True, verbose=1
)


class TimeHistory(tf.keras.callbacks.Callback):
    def on_train_begin(self, logs=None):
        self.start = time.time()
        print("\n=== 학습 시작 ===")

    def on_train_end(self, logs=None):
        elapsed = time.time() - self.start
        print(f"\n총 학습 소요 시간: {elapsed:.2f}초 ({elapsed/60:.2f}분)")


def mixup_generator(x, y, batch_size, alpha=0.2):
    """MixUp 배치 생성기 — 두 이미지를 무작위 비율로 섞고(원본은 uint8 픽셀값
    그대로라 모델 맨 앞 Rescaling 레이어가 알아서 처리함), 라벨도 같은 비율로 섞음.
    라벨 경계가 애매한 데이터(지금 상황)에서 과적합/오버컨피던스를 줄이는 데 씀."""
    n = len(x)
    while True:
        idx1 = np.random.permutation(n)
        idx2 = np.random.permutation(n)
        for start in range(0, n, batch_size):
            end = min(start + batch_size, n)
            i1, i2 = idx1[start:end], idx2[start:end]
            lam = np.random.beta(alpha, alpha, size=len(i1)).astype("float32")
            lam_x = lam.reshape(-1, 1, 1, 1)
            lam_y = lam.reshape(-1, 1)
            bx = x[i1].astype("float32") * lam_x + x[i2].astype("float32") * (1 - lam_x)
            by = y[i1] * lam_y + y[i2] * (1 - lam_y)
            yield bx, by


if _cfg["use_mixup"]:
    print("[augmentation] MixUp 사용 (alpha=0.2) — class_weight은 MixUp과 같이 안 씀")
    steps_per_epoch = max(1, len(x_train) // 16)
    history = model.fit(
        mixup_generator(x_train, y_train_encoded, batch_size=16),
        steps_per_epoch=steps_per_epoch,
        epochs=50,
        validation_data=(x_test, y_test_encoded),
        callbacks=[early_stopping, checkpoint, TimeHistory()],
        # MixUp 쓸 때는 class_weight을 같이 안 씀 (라벨 자체가 이미 섞여있어서 정수 클래스
        # 기준 가중치가 제대로 안 먹힘 — 대신 MixUp 자체가 클래스 간 균형에 도움을 줌)
    )
else:
    history = model.fit(
        x_train, y_train_encoded,
        epochs=50,
        batch_size=16,
        validation_data=(x_test, y_test_encoded),
        callbacks=[early_stopping, checkpoint, TimeHistory()],
        class_weight=class_weight_dict,
    )

# ------------------------------------------------------------------
# 3-1. 미세조정 (Fine-tuning) — MobileNetV2 상위 일부 층을 풀어서 추가 학습
#    1차(freeze) 학습은 "일반 사물" 특징만 재사용하는 수준이라, 여기서 상위 층 일부를
#    아주 낮은 학습률로 살짝 더 학습시켜 얼굴형처럼 미세한 차이를 더 잘 잡게 합니다.
#    시간이 부족하면 FINE_TUNE = False 로 끄고 1차 결과만 써도 됩니다.
# ------------------------------------------------------------------
FINE_TUNE = True
FINE_TUNE_LAYERS = _cfg["fine_tune_layers"]  # 성별별 값: 남성 30, 여성 50 (상단 _GENDER_CONFIG 참고)

if FINE_TUNE:
    print("\n" + "=" * 50)
    print(" 미세조정(fine-tuning) 시작")
    print("=" * 50)

    base_model.trainable = True
    for layer in base_model.layers[:-FINE_TUNE_LAYERS]:
        layer.trainable = False  # 상위 일부 층만 남기고 나머지는 계속 고정

    # BatchNormalization 층은 상위 30개 안에 있어도 계속 얼려둠.
    # (작은 배치·적은 데이터로 BatchNorm 통계까지 같이 흔들면 학습이 불안정해져서
    #  fine-tune 시작 지점에 loss가 확 튀는 현상이 생김 — 이걸 막는 표준적인 방법)
    for layer in base_model.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False

    # 학습률을 아주 낮게 — 이미 학습된 특징이 크게 망가지지 않도록
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss=loss_fn,  # 1차와 동일하게 label_smoothing 유지
        metrics=["acc"],
    )

    fine_tune_early_stopping = EarlyStopping(
        monitor="val_loss", patience=6, verbose=1, restore_best_weights=True
    )
    fine_tune_checkpoint = ModelCheckpoint(
        filepath=f"my_cnn_model_faceshape_{GENDER}_finetuned.h5",
        monitor="val_loss", save_best_only=True, verbose=1,
    )
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss", factor=0.5, patience=3, min_lr=1e-7, verbose=1
    )

    if _cfg["use_mixup"]:
        history_ft = model.fit(
            mixup_generator(x_train, y_train_encoded, batch_size=16),
            steps_per_epoch=max(1, len(x_train) // 16),
            epochs=30,
            validation_data=(x_test, y_test_encoded),
            callbacks=[fine_tune_early_stopping, fine_tune_checkpoint, reduce_lr],
        )
    else:
        history_ft = model.fit(
            x_train, y_train_encoded,
            epochs=30,
            batch_size=16,
            validation_data=(x_test, y_test_encoded),
            callbacks=[fine_tune_early_stopping, fine_tune_checkpoint, reduce_lr],
            class_weight=class_weight_dict,
        )

# ------------------------------------------------------------------
# 4. 평가
# ------------------------------------------------------------------
test_loss, test_acc = model.evaluate(x_test, y_test_encoded, verbose=0)
print(f"\nFinal Best Test Accuracy: {test_acc:.4f}")

y_pred = model.predict(x_test, verbose=0)
y_pred_classes = np.argmax(y_pred, axis=1)

print("\n[상세 분류 성능 리포트]")
print(classification_report(y_test, y_pred_classes, target_names=CLASS_NAMES))
print("[혼동 행렬]")
print(confusion_matrix(y_test, y_pred_classes))

# 학습 곡선 (미세조정을 했으면 이어붙여서 하나의 그래프로 표시)
if FINE_TUNE:
    acc = history.history["acc"] + history_ft.history["acc"]
    val_acc = history.history["val_acc"] + history_ft.history["val_acc"]
    loss = history.history["loss"] + history_ft.history["loss"]
    val_loss = history.history["val_loss"] + history_ft.history["val_loss"]
    fine_tune_start_epoch = len(history.history["acc"])
else:
    acc = history.history["acc"]
    val_acc = history.history["val_acc"]
    loss = history.history["loss"]
    val_loss = history.history["val_loss"]
    fine_tune_start_epoch = None

plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(acc, label="Train Accuracy", marker="o")
plt.plot(val_acc, label="Validation Accuracy", marker="x")
if fine_tune_start_epoch:
    plt.axvline(fine_tune_start_epoch - 0.5, color="gray", linestyle="--", label="Fine-tune 시작")
plt.title("Model Accuracy"); plt.xlabel("Epoch"); plt.ylabel("Accuracy"); plt.legend(); plt.grid(True)
plt.subplot(1, 2, 2)
plt.plot(loss, label="Train Loss", marker="o")
plt.plot(val_loss, label="Validation Loss", marker="x")
if fine_tune_start_epoch:
    plt.axvline(fine_tune_start_epoch - 0.5, color="gray", linestyle="--", label="Fine-tune 시작")
plt.title("Model Loss"); plt.xlabel("Epoch"); plt.ylabel("Loss"); plt.legend(); plt.grid(True)
plt.tight_layout()
plt.savefig(f"training_curve_{GENDER}.png")
print(f"학습 곡선을 training_curve_{GENDER}.png로 저장했습니다.")

# ------------------------------------------------------------------
# 5. Jetson 이식용 가중치 추출 (핵심 — 이걸 빼먹으면 Jetson에서 못 씀)
# ------------------------------------------------------------------
weights = model.get_weights()
np.savez(f"faceshape_weights_{GENDER}.npz", *weights)
print(f"\nJetson 이식용 가중치 저장 완료: faceshape_weights_{GENDER}.npz ({len(weights)}개 배열)")
print(f"이 파일을 faceshape_project/ 폴더의 faceshape_weights_{GENDER}.npz 자리에 넣으면 됩니다.")
print("men, women 둘 다 끝났으면 GENDER를 바꿔서 반대쪽도 실행하세요 (아직 안 했다면).")