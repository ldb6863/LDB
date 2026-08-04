# -*- coding: utf-8 -*-
"""
core/glasses_ar.py
===================
안경 AR 합성 클래스. 팀원이 만든 개선판(얼굴 폭 기반 크기 조절 + 눈 기울기 기반
회전 + 콧대 위치 기준 정렬)을 그대로 이식했습니다.

jetson_client.py의 try_apply_ar()에서 이렇게 씁니다:
    ar = GlassesAR(image_path)
    frame = ar.overlay_glasses(frame, landmarks, image_shape)
여기서 landmarks는 core.landmark_analyzer.detect_face_and_landmarks()가 돌려주는
dict 안의 "_raw_landmarks"(mediapipe 원본 좌표 리스트)를 그대로 넘겨야 합니다.

인스턴스를 안경 종류(경로)마다 새로 만드는 게 아니라, jetson_client.py에서
경로별로 캐싱해서 재사용합니다(ar_cache) — 매번 새로 만들면 파일을 계속
다시 읽어서 느려지기 때문입니다.
"""

import cv2
import numpy as np
import math


class GlassesAR:
    def __init__(self, glasses_path):
        # 알파 채널(투명도, PNG)을 포함하여 안경 이미지 읽기
        self.glasses_img = cv2.imread(glasses_path, cv2.IMREAD_UNCHANGED)

        if self.glasses_img is None:
            raise FileNotFoundError(f"안경 이미지 경로를 찾을 수 없습니다: {glasses_path}")

        if self.glasses_img.shape[2] != 4:
            raise ValueError(
                f"안경 이미지에 알파(투명도) 채널이 없습니다: {glasses_path} "
                f"(PNG로 배경을 투명하게 저장했는지 확인하세요)"
            )

    def overlay_glasses(self, frame, landmarks, image_shape):
        """얼굴 크기와 기울기(회전)를 계산해서 안경을 합성합니다.
        landmarks: mediapipe 원본 좌표 리스트 (예: landmarks[33].x 형태로 접근 가능)
        image_shape: frame.shape (h, w, c)
        """
        h, w = image_shape[0], image_shape[1]

        try:
            # 1. 핵심 랜드마크 추출
            left_eye = (int(landmarks[33].x * w), int(landmarks[33].y * h))
            right_eye = (int(landmarks[263].x * w), int(landmarks[263].y * h))
            left_cheek = (int(landmarks[234].x * w), int(landmarks[234].y * h))
            right_cheek = (int(landmarks[454].x * w), int(landmarks[454].y * h))
            nose_bridge = (int(landmarks[168].x * w), int(landmarks[168].y * h))

            # 2. 안경 사이즈 — 얼굴 전체 너비 기준, 살짝(1.15배) 여유 있게
            face_width = math.hypot(right_cheek[0] - left_cheek[0], right_cheek[1] - left_cheek[1])
            glasses_width = int(face_width * 1.15)
            if glasses_width <= 0:
                return frame

            g_h, g_w = self.glasses_img.shape[:2]
            glasses_height = int(glasses_width * (g_h / g_w))
            if glasses_height <= 0:
                return frame

            # 3. 고개 기울기(회전 각도) — 양쪽 눈 높낮이 차이로 계산
            dY = right_eye[1] - left_eye[1]
            dX = right_eye[0] - left_eye[0]
            angle = np.degrees(np.arctan2(dY, dX))
            # 주의: cv2.getRotationMatrix2D의 각도 방향이 이 각도 계산 방향과
            # 반대라서(팀원 코드에도 있던 버그), 부호를 뒤집어야 실제 고개 기울기랑
            # 같은 방향으로 안경이 돌아감. 안 뒤집으면 사람이 기운 반대 방향으로 돎.

            # 4. 리사이즈 + 회전
            resized_glasses = cv2.resize(
                self.glasses_img, (glasses_width, glasses_height), interpolation=cv2.INTER_AREA
            )
            M = cv2.getRotationMatrix2D((glasses_width // 2, glasses_height // 2), -angle, 1.0)
            rotated_glasses = cv2.warpAffine(
                resized_glasses, M, (glasses_width, glasses_height),
                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0)
            )

            # 5. 합성 위치 — X축은 양 눈 중앙, Y축은 콧대 기준
            center_x = (left_eye[0] + right_eye[0]) // 2
            center_y = nose_bridge[1] + int(glasses_height * 0.08)

            x1 = center_x - (glasses_width // 2)
            y1 = center_y - (glasses_height // 2)
            x2 = x1 + glasses_width
            y2 = y1 + glasses_height

            # 화면 밖으로 나가면 합성 스킵 (에러 방지)
            if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                return frame

            alpha_channel = rotated_glasses[:, :, 3] / 255.0
            alpha_mask = cv2.merge((alpha_channel, alpha_channel, alpha_channel))
            glasses_rgb = rotated_glasses[:, :, :3]

            roi = frame[y1:y2, x1:x2].astype(float)
            blended = (glasses_rgb.astype(float) * alpha_mask) + (roi * (1.0 - alpha_mask))
            frame[y1:y2, x1:x2] = blended.astype(np.uint8)

        except Exception:
            # 랜드마크 좌표가 일시적으로 튀거나 계산 에러 시 원본 프레임 그대로 유지
            pass

        return frame