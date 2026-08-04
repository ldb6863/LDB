# -*- coding: utf-8 -*-
"""얼굴 상세 지표 + 상체 비율만 빠르게 확인하는 통합 테스트 도구입니다."""

import os
import cv2
from core import landmark_analyzer
from core.body_analyzer import BodyAnalyzer


def main():
    body = BodyAnalyzer(enable_segmentation=False)
    cap = cv2.VideoCapture(0)
    frame_count = 0
    print("얼굴과 어깨가 함께 나오게 앉아주세요. Q로 종료합니다.")

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        _, landmarks = landmark_analyzer.detect_face_and_landmarks(frame)
        face_metrics, face_tags = landmark_analyzer.extract_detailed_face_metrics(landmarks)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_result = body.pose.process(rgb)
        body_metrics, body_tags = {}, []
        if pose_result.pose_landmarks:
            face_width = face_metrics.get("얼굴 너비(px)")
            body_metrics, body_tags = body.analyze_body_proportions(
                pose_result.pose_landmarks.landmark, w, h, face_width_px=face_width
            )
            body.mp_drawing.draw_landmarks(frame, pose_result.pose_landmarks, body.mp_pose.POSE_CONNECTIONS)

        if frame_count % 30 == 0:
            os.system("cls" if os.name == "nt" else "clear")
            print("[얼굴 지표]")
            for key, value in face_metrics.items():
                print(f"- {key}: {value:.3f}")
            print("\n[얼굴 태그]")
            for tag in face_tags:
                print(f"- {tag}")
            print("\n[상체 지표]")
            for key, value in body_metrics.items():
                print(f"- {key}: {value:.3f}")
            print("\n[상체 태그]")
            for tag in body_tags:
                print(f"- {tag}")

        cv2.imshow("Face + Body Test", frame)
        frame_count += 1
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27):
            break

    cap.release()
    body.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
