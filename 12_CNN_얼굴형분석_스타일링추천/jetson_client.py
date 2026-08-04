# -*- coding: utf-8 -*-
"""
jetson_client.py — 15초 누적 얼굴+상체 분석 통합본
====================================================
기존 프로젝트 기능:
- M/F 성별 선택
- 현재 MobileNetV2 성별 모델과 최신 CNN+랜드마크 앙상블
- 안경 추천, 추천 선택, Y/N 피드백 DB 기록

팀원 코드에서 추가한 기능:
- 15초 카운트다운 분석
- 여러 번의 얼굴형 판정을 누적해 최종 다수결
- 상세 얼굴 지표/복합 태그 누적
- MediaPipe Pose 상체 비율 태그 누적
- 0초에 콘솔로 기본 컷/볼륨/기장/앞머리/유의사항 종합 출력

키:
- 시작 화면: M=남성, F=여성, ESC=종료
- 결과 화면: 1=헤어 선택, 2/3=안경 선택, Y/N=피드백
- R=같은 성별로 다시 15초 분석, G=성별 선택으로 복귀, ESC=종료
"""

import os
import time
from collections import Counter

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core import cnn_classifier, ensemble, landmark_analyzer, glasses_ar
from core.body_analyzer import BodyAnalyzer
from core.styling_recommender import (
    build_full_recommendation,
    print_final_report,
    reliable_tags,
)
import db_local as db

ANALYSIS_DURATION_SEC = 15
CNN_SAMPLE_INTERVAL_SEC = 2.2   # TTA 5장 기준 약 6~7회 판정
TAG_SAMPLE_INTERVAL_SEC = 0.5
POSE_FRAME_INTERVAL = 3
CONSOLE_UPDATE_INTERVAL_SEC = 1.0
USE_TTA = True
# AR은 이제 상시 on/off 상수가 아니라, 결과 화면에서 A키로 그때그때 토글합니다
# (main() 안의 ar_active 변수 참고).
BODY_SEGMENTATION_ENABLED = False  # 실험적 목 두께 기능은 기본 비활성화

_FONT_CANDIDATES = [
    "malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

FONT = None
FONT_SMALL = None
for path in _FONT_CANDIDATES:
    try:
        FONT = ImageFont.truetype(path, 19)
        FONT_SMALL = ImageFont.truetype(path, 16)
        print(f"[jetson_client] 폰트 로드 성공: {path}")
        break
    except IOError:
        continue
if FONT is None:
    print("[경고] 한글 폰트를 찾지 못했습니다. sudo apt install -y fonts-nanum")
    FONT = ImageFont.load_default()
    FONT_SMALL = FONT


def draw_text(frame_bgr, text, pos, color=(255, 255, 255), small=False):
    pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    draw.text(pos, text, font=FONT_SMALL if small else FONT, fill=color)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


import traceback

ERROR_LOG_PATH = "app_errors.log"


def _log_error(context, exc):
    """화면은 1초마다 지워지니까, 에러가 나면 화면 말고 파일에도 남겨서
    나중에(발표 중 이상 동작 시) 원인 추적 가능하게 함."""
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {context}\n")
            f.write(traceback.format_exc())
    except Exception:
        pass  # 로그 기록 자체가 실패해도 본 프로그램은 안 죽게


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def draw_gender_prompt(frame):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 105), (25, 25, 25), -1)
    frame = cv2.addWeighted(overlay, 0.65, frame, 0.35, 0)
    frame = draw_text(frame, "성별 선택 — M: 남성 / F: 여성", (25, 24))
    frame = draw_text(frame, "선택 후 15초 동안 얼굴과 어깨를 함께 분석합니다.", (25, 60), (210, 230, 255), small=True)
    return frame


def draw_analysis_overlay(frame, remaining, current_shape, current_conf, face_ok, body_ok, samples):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 125), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.62, frame, 0.38, 0)

    frame = draw_text(frame, f"분석 중: {remaining}초", (22, 15), (255, 230, 120))
    status = f"얼굴: {'인식' if face_ok else '대기'} / 상체: {'인식' if body_ok else '대기'} / CNN 샘플: {samples}회"
    frame = draw_text(frame, status, (22, 49), (220, 220, 220), small=True)
    if current_shape:
        frame = draw_text(frame, f"현재 판정: {current_shape} ({current_conf:.0f}%)", (22, 77), (120, 255, 220), small=True)
    frame = draw_text(frame, "정면을 보고 어깨까지 화면에 나오게 유지해주세요.", (22, 102), (190, 210, 255), small=True)
    return frame


def _draw_wrapped(frame, text, x, y, max_chars=29, line_height=24, color=(225, 225, 225)):
    text = str(text)
    lines = []
    while len(text) > max_chars:
        cut = text.rfind(" ", 0, max_chars + 1)
        if cut <= 0:
            cut = max_chars
        lines.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        lines.append(text)
    for line in lines:
        frame = draw_text(frame, line, (x, y), color, small=True)
        y += line_height
    return frame, y


def draw_result_panel(frame, gender, face_shape, confidence, recommendation,
                      glasses_rec, selected_type, selected_idx, awaiting_feedback,
                      face_tags, body_tags, ar_active=False):
    h, w = frame.shape[:2]
    panel_w = min(470, w - 300)
    x0 = w - panel_w
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, 0), (w, h), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.72, frame, 0.28, 0)

    y = 15
    frame = draw_text(frame, f"{'남성' if gender == 'M' else '여성'} / {face_shape} ({confidence:.0f}%)", (x0 + 12, y), (255, 255, 255))
    y += 38

    labels = [
        ("기본 컷", recommendation["기본 컷"]),
        ("볼륨", recommendation["볼륨 위치"]),
        ("기장", recommendation["기장"]),
        ("앞머리", recommendation["앞머리"]),
    ]
    for label, value in labels:
        frame = draw_text(frame, f"[{label}]", (x0 + 12, y), (150, 255, 190), small=True)
        y += 22
        frame, y = _draw_wrapped(frame, value, x0 + 25, y, max_chars=31, line_height=22)
        y += 5

    frame = draw_text(frame, "1. 헤어 추천 선택", (x0 + 12, y),
                      (0, 255, 255) if selected_type == "hair" else (235, 235, 235), small=True)
    y += 26
    for i, (name, _path, _reason) in enumerate(glasses_rec[:2]):
        active = selected_type == "glasses" and selected_idx == i
        frame = draw_text(frame, f"{i + 2}. {name}", (x0 + 12, y),
                          (0, 255, 255) if active else (235, 235, 235), small=True)
        y += 24

    if selected_type == "glasses" and glasses_rec:
        ar_text = f"A: 안경 {'벗기' if ar_active else '써보기'} {'(착용중)' if ar_active else ''}"
        frame = draw_text(frame, ar_text, (x0 + 12, y), (255, 200, 0) if ar_active else (200, 200, 200), small=True)
        y += 24

    if face_tags:
        y += 8
        frame = draw_text(frame, f"얼굴 특징: {face_tags[0]}", (x0 + 12, y), (190, 220, 255), small=True)
        y += 23
    if body_tags:
        frame = draw_text(frame, f"상체 특징: {body_tags[0]}", (x0 + 12, y), (190, 220, 255), small=True)
        y += 23

    y = min(y + 8, h - 70)
    if awaiting_feedback:
        frame = draw_text(frame, "Y: 좋아요 / N: 별로예요", (x0 + 12, y), (255, 255, 0), small=True)
    else:
        frame = draw_text(frame, "R: 재분석 / G: 성별 변경", (x0 + 12, y), (200, 200, 200), small=True)
    return frame


def reset_scan_state():
    return {
        "start_time": time.time(),
        "last_cnn_time": -1e9,
        "last_tag_time": -1e9,
        "last_console_time": -1e9,
        "frame_count": 0,
        "shape_votes": Counter(),
        "shape_confidences": {},
        "method_counts": Counter(),
        "face_tag_counts": Counter(),
        "body_tag_counts": Counter(),
        "modifier_tag_counts": Counter(),
        "face_tag_samples": 0,
        "body_tag_samples": 0,
        "current_shape": None,
        "current_confidence": 0.0,
        "current_method": None,
        "last_face_metrics": {},
        "last_face_tags": [],
        "last_body_metrics": {},
        "last_landmarks": None,
    }


def finalize_scan(scan, gender):
    if not scan["shape_votes"]:
        return None

    face_shape, _ = scan["shape_votes"].most_common(1)[0]
    winning_conf = scan["shape_confidences"].get(face_shape, [])
    confidence = sum(winning_conf) / len(winning_conf) if winning_conf else scan["current_confidence"]

    face_tags = reliable_tags(scan["face_tag_counts"], scan["face_tag_samples"])
    body_tags = reliable_tags(scan["body_tag_counts"], scan["body_tag_samples"])
    modifier_tags = reliable_tags(scan["modifier_tag_counts"], scan["face_tag_samples"], min_ratio=0.30)
    recommendation = build_full_recommendation(gender, face_shape, face_tags, body_tags)

    print_final_report(
        gender,
        face_shape,
        confidence,
        recommendation,
        face_tags,
        body_tags,
        ANALYSIS_DURATION_SEC,
        method_counts=scan["method_counts"],
    )

    return {
        "face_shape": face_shape,
        "confidence": confidence,
        "face_tags": face_tags,
        "body_tags": body_tags,
        "modifier_tags": modifier_tags,
        "recommendation": recommendation,
        "landmarks": scan["last_landmarks"],
    }


def try_apply_ar(frame, landmarks, image_path, cache):
    """ar_active(사용자가 A키로 켠 상태)일 때만 호출되는 걸 전제로 함.
    여기서는 켜졌는지 여부는 신경 안 쓰고, 실제 합성 시도만 담당."""
    if not image_path or landmarks is None:
        return frame
    raw = landmarks.get("_raw_landmarks") if isinstance(landmarks, dict) else None
    if raw is None:
        return frame
    try:
        if image_path not in cache:
            cache[image_path] = glasses_ar.GlassesAR(image_path)
        return cache[image_path].overlay_glasses(frame, raw, frame.shape)
    except Exception as exc:
        print(f"[AR 경고] {exc}")
        return frame


def main():
    db.init_db()
    cnn_classifier.load_model(".", transfer=True)
    body_analyzer = BodyAnalyzer(enable_segmentation=BODY_SEGMENTATION_ENABLED)

    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not camera.isOpened():
        print("에러: 카메라를 열 수 없습니다.")
        return

    state = "gender"
    gender = None
    scan = None
    result = None
    glasses_rec = []
    selected_type = None
    selected_idx = 0
    awaiting_feedback = False
    ar_active = False  # 결과 화면에서 A키로 켜고 끄는 안경 AR 토글
    panel_visible = True  # 결과 화면에서 P키로 켜고 끄는 정보 패널 토글 (본인 모습 보기용)
    ar_cache = {}

    print("M/F 성별 선택 → 15초 분석 → 콘솔/화면 종합 추천")

    while True:
        ret, frame = camera.read()
        if not ret:
            continue
        frame = cv2.flip(frame, 1)
        key = -1

        if state == "gender":
            frame = draw_gender_prompt(frame)

        elif state == "scan":
            now = time.time()
            elapsed = now - scan["start_time"]
            remaining = max(0, ANALYSIS_DURATION_SEC - int(elapsed))
            h, w = frame.shape[:2]

            face_crop, landmarks = landmark_analyzer.detect_face_and_landmarks(frame)
            face_ok = face_crop is not None and landmarks is not None
            body_ok = False
            current_face_tags = []
            current_body_tags = []

            if face_ok:
                scan["last_landmarks"] = landmarks

                # 세부 지표 계산(삼각함수 여러 번 씀)은 무겁고, 실제로는 0.5초에
                # 한 번만 결과를 쓰는데도 예전엔 매 프레임(초당 15~30번) 계산하고
                # 버렸음 — 이제 필요한 시점에만 계산하도록 게이트 안으로 이동.
                if now - scan["last_tag_time"] >= TAG_SAMPLE_INTERVAL_SEC:
                    base_metrics = landmark_analyzer.extract_face_metrics(landmarks)
                    modifier_tags = landmark_analyzer.get_modifier_tags(base_metrics)
                    detailed_metrics, computed_face_tags = landmark_analyzer.extract_detailed_face_metrics(landmarks)
                    scan["last_face_metrics"] = detailed_metrics
                    scan["last_face_tags"] = computed_face_tags

                    scan["face_tag_counts"].update(set(computed_face_tags))
                    scan["modifier_tag_counts"].update(set(modifier_tags))
                    scan["face_tag_samples"] += 1
                    scan["last_tag_time"] = now

                # 화면/콘솔 표시는 이번 프레임에 새로 계산했든 안 했든 최신 캐시값을 씀
                current_face_tags = scan["last_face_tags"]

                if now - scan["last_cnn_time"] >= CNN_SAMPLE_INTERVAL_SEC:
                    try:
                        shape, conf, method = ensemble.predict_face_shape_ensemble(
                            face_crop, landmarks, gender, use_tta=USE_TTA
                        )
                        scan["shape_votes"][shape] += 1
                        scan["shape_confidences"].setdefault(shape, []).append(conf)
                        scan["method_counts"][method] += 1
                        scan["current_shape"] = shape
                        scan["current_confidence"] = conf
                        scan["current_method"] = method
                        scan["last_cnn_time"] = now
                    except Exception as exc:
                        print(f"[CNN/앙상블 경고] {exc}")
                        _log_error("CNN/앙상블", exc)

            if scan["frame_count"] % POSE_FRAME_INTERVAL == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_result = body_analyzer.pose.process(rgb)
                if pose_result.pose_landmarks:
                    body_ok = True
                    face_width_px = scan["last_face_metrics"].get("얼굴 너비(px)")
                    seg = pose_result.segmentation_mask if BODY_SEGMENTATION_ENABLED else None
                    body_metrics, current_body_tags = body_analyzer.analyze_body_proportions(
                        pose_result.pose_landmarks.landmark,
                        w,
                        h,
                        segmentation_mask=seg,
                        face_width_px=face_width_px,
                    )
                    scan["last_body_metrics"] = body_metrics
                    scan["body_tag_counts"].update(set(current_body_tags))
                    scan["body_tag_samples"] += 1

            frame = draw_analysis_overlay(
                frame,
                remaining,
                scan["current_shape"],
                scan["current_confidence"],
                face_ok,
                body_ok or bool(scan["last_body_metrics"]),
                sum(scan["shape_votes"].values()),
            )

            if now - scan["last_console_time"] >= CONSOLE_UPDATE_INTERVAL_SEC:
                clear_console()
                print("=" * 58)
                print(f"[{remaining}초 남음] 얼굴형 + 세부 얼굴 + 상체 누적 분석 중")
                print("=" * 58)
                print(f"현재 얼굴형: {scan['current_shape'] or '대기 중'} "
                      f"({scan['current_confidence']:.1f}%)")
                print(f"누적 판정: {dict(scan['shape_votes'])}")
                if current_face_tags:
                    print("얼굴 태그:")
                    for tag in current_face_tags:
                        print(f"  - {tag}")
                if current_body_tags:
                    print("상체 태그:")
                    for tag in current_body_tags:
                        print(f"  - {tag}")
                print("정면을 보고 어깨까지 화면에 나오게 유지해주세요.")
                scan["last_console_time"] = now

            scan["frame_count"] += 1

            if elapsed >= ANALYSIS_DURATION_SEC:
                result = finalize_scan(scan, gender)
                if result is None:
                    print("[결과] 얼굴 판정 샘플을 확보하지 못했습니다. R키로 다시 시도하세요.")
                    result = {
                        "face_shape": "Unknown",
                        "confidence": 0.0,
                        "face_tags": [],
                        "body_tags": [],
                        "modifier_tags": [],
                        "recommendation": build_full_recommendation(gender, "", [], []),
                        "landmarks": None,
                    }
                glasses_rec = db.get_glasses_recommendation(result["face_shape"])
                state = "result"
                selected_type = None
                awaiting_feedback = False

        elif state == "result":
            if ar_active and selected_type == "glasses" and glasses_rec:
                # 15초 스캔 끝났을 때 좌표 한 장에 고정하지 않고, 결과 화면에서도
                # 매 프레임 얼굴을 다시 찾아서 안경이 실시간으로 따라오게 함
                _, live_landmarks = landmark_analyzer.detect_face_and_landmarks(frame)
                if live_landmarks is not None:
                    frame = try_apply_ar(frame, live_landmarks, glasses_rec[selected_idx][1], ar_cache)

            if panel_visible:
                frame = draw_result_panel(
                    frame,
                    gender,
                    result["face_shape"],
                    result["confidence"],
                    result["recommendation"],
                    glasses_rec,
                    selected_type,
                    selected_idx,
                    awaiting_feedback,
                    result["face_tags"],
                    result["body_tags"],
                    ar_active,
                )
            else:
                h_, w_ = frame.shape[:2]
                frame = draw_text(frame, "P: 정보 패널 다시 보기", (w_ - 220, h_ - 25), (200, 200, 200), small=True)

        cv2.imshow("Face Styling Recommender", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        if state == "gender":
            if key in (ord("m"), ord("M")):
                gender = "M"
                scan = reset_scan_state()
                state = "scan"
                clear_console()
                print("남성 선택: 15초 분석을 시작합니다.")
            elif key in (ord("f"), ord("F")):
                gender = "F"
                scan = reset_scan_state()
                state = "scan"
                clear_console()
                print("여성 선택: 15초 분석을 시작합니다.")

        elif state == "result":
            if key == ord("1"):
                selected_type = "hair"
                selected_idx = 0
                awaiting_feedback = True
                ar_active = False
            elif key == ord("2") and len(glasses_rec) > 0:
                selected_type = "glasses"
                selected_idx = 0
                awaiting_feedback = True
                ar_active = False  # 새로 선택한 거라 다시 A눌러서 써봐야 함
            elif key == ord("3") and len(glasses_rec) > 1:
                selected_type = "glasses"
                selected_idx = 1
                awaiting_feedback = True
                ar_active = False
            elif key in (ord("a"), ord("A")) and selected_type == "glasses" and glasses_rec:
                ar_active = not ar_active
                print(f"AR 안경 {'착용' if ar_active else '해제'}: {glasses_rec[selected_idx][0]}")
            elif key in (ord("p"), ord("P")):
                panel_visible = not panel_visible
                print(f"정보 패널 {'표시' if panel_visible else '숨김'} (본인 모습 확인용)")
            elif awaiting_feedback and key in (ord("y"), ord("Y"), ord("n"), ord("N")):
                feedback = "good" if key in (ord("y"), ord("Y")) else "bad"
                if selected_type == "hair":
                    item_name = result["recommendation"]["기본 컷"]
                else:
                    item_name = glasses_rec[selected_idx][0] if glasses_rec else None
                log_tags = result["modifier_tags"] + result["face_tags"] + result["body_tags"]
                db.insert_log(
                    gender,
                    result["face_shape"],
                    result["confidence"],
                    log_tags,
                    selected_type,
                    item_name,
                    feedback,
                )
                print(f"피드백 기록됨: {feedback}")
                awaiting_feedback = False
            elif key in (ord("r"), ord("R")):
                scan = reset_scan_state()
                result = None
                state = "scan"
                ar_active = False
                clear_console()
                print("같은 성별로 15초 재분석을 시작합니다.")
            elif key in (ord("g"), ord("G")):
                gender = None
                result = None
                state = "gender"
                selected_type = None
                awaiting_feedback = False
                ar_active = False
                panel_visible = True

    camera.release()
    body_analyzer.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()