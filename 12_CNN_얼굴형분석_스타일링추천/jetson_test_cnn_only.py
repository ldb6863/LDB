# -*- coding: utf-8 -*-
"""
jetson_test_cnn_only.py
=========================
Jetson Nano에서 CNN(cnn_classifier.py)만 따로 떼서 테스트하는 스크립트.
landmark_analyzer.py, glasses_ar.py는 아예 불러오지 않으므로,
팀원 파트가 아직 준비 안 됐어도 지금 바로 Jetson에서 돌려볼 수 있습니다.

가장 중요한 목적: PC(TensorFlow 2.15)에서 만든 faceshape_weights_*.npz가
Jetson(TensorFlow 2.4.1)에서도 문제없이 로드되는지 확인하는 것.
여기서 에러가 나면 팀원 코드와는 무관한 문제이니, 원인 파악이 훨씬 쉬워집니다.

실행 위치: faceshape_project/ 안에서 실행
(faceshape_weights_men.npz, faceshape_weights_women.npz 가 이 폴더에 있어야 함)
"""

import sys
import os
import cv2

print(f"Python: {sys.version}")
import tensorflow as tf
print(f"TensorFlow: {tf.__version__}")

from core import cnn_classifier

print("\n=== 1. 가중치 로드 시도 (Jetson에서 처음 시도하는 부분) ===")
try:
    cnn_classifier.load_model(".", transfer=True)
    print("[성공] men/women 가중치 둘 다 Jetson에서 정상 로드됨.")
except Exception as e:
    print(f"[실패] {e}")
    print("\n→ PC(TF 2.15)와 Jetson(TF 2.4.1)의 MobileNetV2 내부 구현 차이일 가능성이 높습니다.")
    print("  이 경우 core/cnn_classifier.py의 build_transfer_model()을 Jetson TF 버전에 맞게")
    print("  다시 확인해야 할 수 있습니다 — 이 시점에 알려주시면 같이 대응 방법을 찾아봐요.")
    sys.exit(1)

print("\n=== 2. 웹캠으로 실시간 얼굴형 분류만 테스트 (랜드마크/추천 없이) ===")
print("숫자키 1=남성 / 2=여성 선택, ESC 종료")

camera = cv2.VideoCapture(0)
if not camera.isOpened():
    print("에러: 카메라를 열 수 없습니다.")
    sys.exit(1)

gender = "men"
print(f"현재 성별: {gender} (1=남성 / 2=여성 로 전환)")

# 얼굴 검출은 mediapipe 없이 OpenCV 기본 Haar Cascade로 간단히만 (랜드마크 팀원 파트와 무관하게)
# cv2.data 모듈이 없는 OpenCV 빌드(Jetson 시스템 설치본 등)를 대비해 여러 경로를 시도
_CASCADE_CANDIDATES = []
try:
    _CASCADE_CANDIDATES.append(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except AttributeError:
    pass
_CASCADE_CANDIDATES += [
    "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    "/usr/local/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
    "/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml",
]

cascade_path = None
for _p in _CASCADE_CANDIDATES:
    if os.path.isfile(_p):
        cascade_path = _p
        break

if cascade_path is None:
    print("에러: haarcascade_frontalface_default.xml을 못 찾았습니다.")
    print("터미널에서 아래 명령으로 위치를 찾아서, 결과를 알려주세요:")
    print('  find / -name "haarcascade_frontalface_default.xml" 2>/dev/null')
    sys.exit(1)

print(f"얼굴 검출 파일 경로: {cascade_path}")
face_cascade = cv2.CascadeClassifier(cascade_path)

while True:
    ret, frame = camera.read()
    if not ret:
        continue
    frame = cv2.flip(frame, 1)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face_crop = frame[y:y+h, x:x+w]
        try:
            shape, conf = cnn_classifier.predict_face_shape(face_crop, gender)
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"{shape} ({conf:.0f}%)", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        except Exception as e:
            cv2.putText(frame, f"error: {e}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.putText(frame, f"gender: {gender}", (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    cv2.imshow("CNN-only test (Jetson)", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    elif key == ord('1'):
        gender = "men"
    elif key == ord('2'):
        gender = "women"

camera.release()
cv2.destroyAllWindows()
