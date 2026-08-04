# -*- coding: utf-8 -*-
"""
core/body_analyzer.py
=====================
팀원 코드의 MediaPipe Pose 기반 상체 비율 분석 모듈입니다.
어깨너비, 얼굴 대비 어깨너비, 목 길이, 어깨 기울기를 계산해
헤어 기장/볼륨 추천 태그로 사용합니다.
"""

import math
import mediapipe as mp
import numpy as np


class BodyAnalyzer:
    def __init__(self, enable_segmentation=False):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=enable_segmentation,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.enable_segmentation = enable_segmentation

    @staticmethod
    def get_distance(p1, p2, w, h):
        return math.hypot((p2.x - p1.x) * w, (p2.y - p1.y) * h)

    @staticmethod
    def get_midpoint(p1, p2):
        class _Point:
            pass
        mid = _Point()
        mid.x = (p1.x + p2.x) / 2.0
        mid.y = (p1.y + p2.y) / 2.0
        mid.z = (getattr(p1, "z", 0.0) + getattr(p2, "z", 0.0)) / 2.0
        return mid

    @staticmethod
    def get_horizontal_angle(p1, p2, w, h):
        dx = abs((p2.x - p1.x) * w)
        dy = abs((p2.y - p1.y) * h)
        return math.degrees(math.atan2(dy, max(dx, 1e-6)))

    @staticmethod
    def estimate_neck_width(segmentation_mask, ear_mid, shoulder_mid, w, h):
        """실험적 목 폭 추정 함수. 기본 추천 로직에서는 아직 사용하지 않습니다."""
        if segmentation_mask is None:
            return None
        neck_y_ratio = ear_mid.y + (shoulder_mid.y - ear_mid.y) * 0.6
        neck_y_px = max(0, min(h - 1, int(neck_y_ratio * h)))
        row = segmentation_mask[neck_y_px, :] > 0.5
        if not row.any():
            return None
        xs = np.where(row)[0]
        return float(xs.max() - xs.min())

    def analyze_body_proportions(self, landmarks, w, h, segmentation_mask=None, face_width_px=None):
        tags = []
        metrics = {}

        l_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        r_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        l_ear = landmarks[self.mp_pose.PoseLandmark.LEFT_EAR]
        r_ear = landmarks[self.mp_pose.PoseLandmark.RIGHT_EAR]

        shoulder_mid = self.get_midpoint(l_shoulder, r_shoulder)
        ear_mid = self.get_midpoint(l_ear, r_ear)

        shoulder_width = self.get_distance(l_shoulder, r_shoulder, w, h)
        metrics["어깨 너비(px)"] = shoulder_width

        if face_width_px is not None and face_width_px > 0:
            shoulder_face_ratio = shoulder_width / face_width_px
            metrics["얼굴 대비 어깨너비 비율"] = shoulder_face_ratio
            # 팀원 코드의 실험적 임계값을 그대로 유지합니다.
            if shoulder_face_ratio >= 2.4:
                tags.append("어깨가 넓은 편 (여유 있는 기장/볼륨 추천)")
            elif shoulder_face_ratio <= 2.0:
                tags.append("어깨가 좁은 편 (볼륨감 있는 스타일로 밸런스 추천)")

        neck_length = self.get_distance(ear_mid, shoulder_mid, w, h)
        neck_length_ratio = neck_length / shoulder_width if shoulder_width > 0 else 0
        metrics["목 길이 비율"] = neck_length_ratio
        if neck_length_ratio >= 0.55:
            tags.append("목이 긴 편 (다양한 기장 소화 가능)")
        elif neck_length_ratio <= 0.35:
            tags.append("목이 짧은 편 (기장으로 라인 보완 추천)")

        shoulder_slope = self.get_horizontal_angle(l_shoulder, r_shoulder, w, h)
        metrics["어깨 수평 기울기(도)"] = shoulder_slope
        if shoulder_slope >= 5.0:
            tags.append("좌우 어깨 높이차가 있는 편")

        if self.enable_segmentation and segmentation_mask is not None:
            neck_width = self.estimate_neck_width(segmentation_mask, ear_mid, shoulder_mid, w, h)
            if neck_width is not None:
                metrics["목 너비 추정(px)"] = neck_width

        return metrics, tags

    def close(self):
        try:
            self.pose.close()
        except Exception:
            pass
