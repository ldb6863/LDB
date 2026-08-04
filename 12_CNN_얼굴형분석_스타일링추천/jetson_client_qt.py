# -*- coding: utf-8 -*-
"""
jetson_client_qt.py — PyQt5 UI 버전
=====================================
원본 jetson_client.py(OpenCV 창 + 키보드)를 그대로 두고, 이 파일에서
PyQt5 버튼/레이아웃 UI로 새로 짰습니다. core/, db_local.py 등 로직은
전혀 안 건드리고 그대로 가져다 씁니다.

구조:
- VideoWorker(QThread): 웹캠 읽기 + AI 처리(원본의 while 루프와 로직 동일)를
  백그라운드 스레드에서 계속 돌림. 프레임/상태를 시그널로 UI에 보냄.
- MainWindow(QMainWindow): 왼쪽에 영상, 오른쪽에 버튼/정보 패널.
  버튼 클릭 -> VideoWorker의 명령 큐에 넣기만 함(스레드 세이프하게 lock으로 보호).

설치: pip install PyQt5 --break-system-packages
실행: python3 jetson_client_qt.py
"""

import sys
import time
import threading
import traceback
from collections import Counter

import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QStackedWidget, QFrame, QSizePolicy
)
from PyQt5.QtGui import QImage, QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from core import cnn_classifier, ensemble, landmark_analyzer, glasses_ar
from core.body_analyzer import BodyAnalyzer
from core.styling_recommender import build_full_recommendation, print_final_report, reliable_tags
import db_local as db

ANALYSIS_DURATION_SEC = 15
CNN_SAMPLE_INTERVAL_SEC = 2.2
TAG_SAMPLE_INTERVAL_SEC = 0.5
POSE_FRAME_INTERVAL = 3
USE_TTA = True
BODY_SEGMENTATION_ENABLED = False

ERROR_LOG_PATH = "app_errors.log"


def _log_error(context, exc):
    """Qt 창은 터미널을 안 보고 있을 가능성이 높으니, 에러가 나면 파일에도 남겨서
    나중에 원인 추적 가능하게 함 (원본 jetson_client.py에 있던 것과 동일)."""
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {context}\n")
            f.write(traceback.format_exc())
    except Exception:
        pass


# ------------------------------------------------------------------
# 원본 jetson_client.py의 순수 로직 함수들 (화면 그리기 없는 부분만) 그대로 재사용
# ------------------------------------------------------------------

def reset_scan_state():
    return {
        "start_time": time.time(),
        "last_cnn_time": -1e9,
        "last_tag_time": -1e9,
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

    print_final_report(gender, face_shape, confidence, recommendation, face_tags, body_tags,
                        ANALYSIS_DURATION_SEC, method_counts=scan["method_counts"])

    return {
        "face_shape": face_shape, "confidence": confidence, "face_tags": face_tags,
        "body_tags": body_tags, "modifier_tags": modifier_tags,
        "recommendation": recommendation, "landmarks": scan["last_landmarks"],
    }


def try_apply_ar(frame, landmarks, image_path, cache):
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
        _log_error("AR 합성", exc)
        return frame


# ------------------------------------------------------------------
# 백그라운드 스레드: 웹캠 읽기 + AI 처리 전담
# ------------------------------------------------------------------

class VideoWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    status_update = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._running = True
        self._lock = threading.Lock()
        self._pending = []  # UI 스레드가 넣는 명령 큐: (name, args) 튜플들

        self.state = "gender"
        self.gender = None
        self.scan = None
        self.result = None
        self.glasses_rec = []
        self.selected_type = None
        self.selected_idx = 0
        self.awaiting_feedback = False
        self.ar_active = False
        self.ar_cache = {}
        self.body_analyzer = None

    # ---- UI 스레드에서 호출하는 명령 함수들 (실제 처리는 run() 루프에서) ----
    def queue(self, name, *args):
        with self._lock:
            self._pending.append((name, args))

    def _process_pending(self):
        with self._lock:
            actions = self._pending
            self._pending = []
        for name, args in actions:
            self._handle_action(name, args)

    def _handle_action(self, name, args):
        if name == "set_gender":
            self.gender = args[0]
            self.scan = reset_scan_state()
            self.state = "scan"
        elif name == "select_hair":
            self.selected_type = "hair"
            self.selected_idx = 0
            self.awaiting_feedback = True
            self.ar_active = False
        elif name == "select_glasses":
            self.selected_type = "glasses"
            self.selected_idx = args[0]
            self.awaiting_feedback = True
            self.ar_active = False
        elif name == "toggle_ar":
            if self.selected_type == "glasses" and self.glasses_rec:
                self.ar_active = not self.ar_active
        elif name == "feedback":
            self._save_feedback(args[0])
        elif name == "reanalyze":
            self.scan = reset_scan_state()
            self.result = None
            self.state = "scan"
            self.ar_active = False
        elif name == "change_gender":
            self.gender = None
            self.result = None
            self.state = "gender"
            self.selected_type = None
            self.awaiting_feedback = False
            self.ar_active = False

    def _save_feedback(self, feedback):
        if self.result is None:
            return
        if self.selected_type == "hair":
            item_name = self.result["recommendation"]["기본 컷"]
        else:
            item_name = self.glasses_rec[self.selected_idx][0] if self.glasses_rec else None
        log_tags = self.result["modifier_tags"] + self.result["face_tags"] + self.result["body_tags"]
        db.insert_log(self.gender, self.result["face_shape"], self.result["confidence"],
                       log_tags, self.selected_type, item_name, feedback)
        self.awaiting_feedback = False

    def stop(self):
        self._running = False
        self.wait()

    # ---- 메인 루프 (원본 jetson_client.py의 while True 루프와 로직 동일) ----
    def run(self):
        db.init_db()
        cnn_classifier.load_model(".", transfer=True)
        self.body_analyzer = BodyAnalyzer(enable_segmentation=BODY_SEGMENTATION_ENABLED)

        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not camera.isOpened():
            self.status_update.emit({"error": "카메라를 열 수 없습니다."})
            return

        while self._running:
            self._process_pending()

            ret, frame = camera.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)

            if self.state == "scan" and self.scan is not None:
                self._run_scan_step(frame)
            elif self.state == "result":
                self._run_result_step(frame)

            self.frame_ready.emit(self._to_qimage(frame))
            self.status_update.emit(self._build_status())

        camera.release()
        if self.body_analyzer:
            self.body_analyzer.close()

    def _run_scan_step(self, frame):
        scan = self.scan
        now = time.time()
        elapsed = now - scan["start_time"]
        h, w = frame.shape[:2]

        face_crop, landmarks = landmark_analyzer.detect_face_and_landmarks(frame)
        face_ok = face_crop is not None and landmarks is not None

        if face_ok:
            scan["last_landmarks"] = landmarks
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

            if now - scan["last_cnn_time"] >= CNN_SAMPLE_INTERVAL_SEC:
                try:
                    shape, conf, method = ensemble.predict_face_shape_ensemble(
                        face_crop, landmarks, self.gender, use_tta=USE_TTA
                    )
                    scan["shape_votes"][shape] += 1
                    scan["shape_confidences"].setdefault(shape, []).append(conf)
                    scan["method_counts"][method] += 1
                    scan["current_shape"] = shape
                    scan["current_confidence"] = conf
                    scan["last_cnn_time"] = now
                except Exception as exc:
                    print(f"[CNN/앙상블 경고] {exc}")
                    _log_error("CNN/앙상블", exc)

        if scan["frame_count"] % POSE_FRAME_INTERVAL == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pose_result = self.body_analyzer.pose.process(rgb)
            if pose_result.pose_landmarks:
                face_width_px = scan["last_face_metrics"].get("얼굴 너비(px)")
                body_metrics, body_tags = self.body_analyzer.analyze_body_proportions(
                    pose_result.pose_landmarks.landmark, w, h, face_width_px=face_width_px
                )
                scan["last_body_metrics"] = body_metrics
                scan["body_tag_counts"].update(set(body_tags))
                scan["body_tag_samples"] += 1

        scan["frame_count"] += 1

        if elapsed >= ANALYSIS_DURATION_SEC:
            result = finalize_scan(scan, self.gender)
            if result is None:
                result = {
                    "face_shape": "Unknown", "confidence": 0.0, "face_tags": [], "body_tags": [],
                    "modifier_tags": [], "recommendation": build_full_recommendation(self.gender, "", [], []),
                    "landmarks": None,
                }
            self.result = result
            self.glasses_rec = db.get_glasses_recommendation(result["face_shape"])
            self.state = "result"
            self.selected_type = None
            self.awaiting_feedback = False

    def _run_result_step(self, frame):
        if self.ar_active and self.selected_type == "glasses" and self.glasses_rec:
            _, live_landmarks = landmark_analyzer.detect_face_and_landmarks(frame)
            if live_landmarks is not None:
                frame[:] = try_apply_ar(frame, live_landmarks, self.glasses_rec[self.selected_idx][1], self.ar_cache)

    def _build_status(self):
        scan = self.scan
        remaining = 0
        if self.state == "scan" and scan is not None:
            remaining = max(0, ANALYSIS_DURATION_SEC - int(time.time() - scan["start_time"]))
        return {
            "state": self.state,
            "gender": self.gender,
            "remaining": remaining,
            "current_shape": scan["current_shape"] if scan else None,
            "current_confidence": scan["current_confidence"] if scan else 0.0,
            "result": self.result,
            "glasses_rec": self.glasses_rec,
            "selected_type": self.selected_type,
            "selected_idx": self.selected_idx,
            "awaiting_feedback": self.awaiting_feedback,
            "ar_active": self.ar_active,
        }

    @staticmethod
    def _to_qimage(frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()


# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Styling Recommender")
        self.resize(1280, 760)

        self.worker = VideoWorker()
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.status_update.connect(self._on_status)

        # ---- 왼쪽: 영상 ----
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ---- 오른쪽: 상태별 패널 ----
        self.panel_stack = QStackedWidget()
        self.panel_stack.setFixedWidth(340)

        self.gender_page = self._build_gender_page()
        self.scan_page = self._build_scan_page()
        self.result_page = self._build_result_page()
        self.panel_stack.addWidget(self.gender_page)   # index 0
        self.panel_stack.addWidget(self.scan_page)      # index 1
        self.panel_stack.addWidget(self.result_page)    # index 2

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.panel_stack)
        self.setCentralWidget(central)

        self.worker.start()

    # ---- 페이지 구성 ----
    def _build_gender_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        title = QLabel("성별을 선택해주세요")
        title.setFont(QFont("", 14, QFont.Bold))
        v.addWidget(title)
        v.addWidget(QLabel("선택 후 15초 동안 얼굴과 어깨를 함께 분석합니다."))
        btn_m = QPushButton("남성")
        btn_f = QPushButton("여성")
        btn_m.setMinimumHeight(60)
        btn_f.setMinimumHeight(60)
        btn_m.clicked.connect(lambda: self.worker.queue("set_gender", "M"))
        btn_f.clicked.connect(lambda: self.worker.queue("set_gender", "F"))
        v.addWidget(btn_m)
        v.addWidget(btn_f)
        v.addStretch()
        return w

    def _build_scan_page(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.scan_remaining_label = QLabel("분석 중: 15초")
        self.scan_remaining_label.setFont(QFont("", 16, QFont.Bold))
        self.scan_shape_label = QLabel("현재 판정: -")
        v.addWidget(self.scan_remaining_label)
        v.addWidget(self.scan_shape_label)
        v.addWidget(QLabel("정면을 보고 어깨까지 화면에 나오게 유지해주세요."))
        v.addStretch()
        return w

    def _build_result_page(self):
        w = QWidget()
        v = QVBoxLayout(w)

        self.result_title_label = QLabel("-")
        self.result_title_label.setFont(QFont("", 13, QFont.Bold))
        v.addWidget(self.result_title_label)

        self.reco_label = QLabel("")
        self.reco_label.setWordWrap(True)
        v.addWidget(self.reco_label)

        v.addWidget(self._hline())

        self.btn_hair = QPushButton("1. 헤어 추천 선택")
        self.btn_hair.clicked.connect(lambda: self.worker.queue("select_hair"))
        v.addWidget(self.btn_hair)

        self.btn_glasses1 = QPushButton("2. 안경 옵션 1")
        self.btn_glasses1.clicked.connect(lambda: self.worker.queue("select_glasses", 0))
        v.addWidget(self.btn_glasses1)

        self.btn_glasses2 = QPushButton("3. 안경 옵션 2")
        self.btn_glasses2.clicked.connect(lambda: self.worker.queue("select_glasses", 1))
        v.addWidget(self.btn_glasses2)

        self.btn_ar = QPushButton("안경 써보기 (AR)")
        self.btn_ar.clicked.connect(lambda: self.worker.queue("toggle_ar"))
        self.btn_ar.setEnabled(False)
        v.addWidget(self.btn_ar)

        v.addWidget(self._hline())

        feedback_row = QHBoxLayout()
        self.btn_good = QPushButton("좋아요")
        self.btn_bad = QPushButton("별로예요")
        self.btn_good.clicked.connect(lambda: self.worker.queue("feedback", "good"))
        self.btn_bad.clicked.connect(lambda: self.worker.queue("feedback", "bad"))
        feedback_row.addWidget(self.btn_good)
        feedback_row.addWidget(self.btn_bad)
        v.addLayout(feedback_row)

        v.addWidget(self._hline())

        self.tags_label = QLabel("")
        self.tags_label.setWordWrap(True)
        v.addWidget(self.tags_label)

        v.addStretch()

        bottom_row = QHBoxLayout()
        self.btn_reanalyze = QPushButton("재분석 (R)")
        self.btn_change_gender = QPushButton("성별 변경 (G)")
        self.btn_reanalyze.clicked.connect(lambda: self.worker.queue("reanalyze"))
        self.btn_change_gender.clicked.connect(lambda: self.worker.queue("change_gender"))
        bottom_row.addWidget(self.btn_reanalyze)
        bottom_row.addWidget(self.btn_change_gender)
        v.addLayout(bottom_row)

        return w

    @staticmethod
    def _hline():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        return line

    # ---- 워커 시그널 처리 ----
    def _on_frame(self, qimg):
        pix = QPixmap.fromImage(qimg)
        pix = pix.scaled(self.video_label.width(), self.video_label.height(),
                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(pix)

    def _on_status(self, status):
        if status.get("error"):
            self.video_label.setText(status["error"])
            return

        state = status["state"]
        if state == "gender":
            self.panel_stack.setCurrentIndex(0)
        elif state == "scan":
            self.panel_stack.setCurrentIndex(1)
            self.scan_remaining_label.setText(f"분석 중: {status['remaining']}초")
            shape = status["current_shape"] or "대기 중"
            self.scan_shape_label.setText(f"현재 판정: {shape} ({status['current_confidence']:.0f}%)")
        elif state == "result":
            self.panel_stack.setCurrentIndex(2)
            self._update_result_page(status)

    def _update_result_page(self, status):
        result = status["result"]
        if result is None:
            return
        gender_text = "남성" if status["gender"] == "M" else "여성"
        self.result_title_label.setText(f"{gender_text} / {result['face_shape']} ({result['confidence']:.0f}%)")

        reco = result["recommendation"]
        reco_text = (
            f"[기본 컷] {reco['기본 컷']}\n"
            f"[볼륨] {reco['볼륨 위치']}\n"
            f"[기장] {reco['기장']}\n"
            f"[앞머리] {reco['앞머리']}"
        )
        self.reco_label.setText(reco_text)

        glasses_rec = status["glasses_rec"]
        self.btn_glasses1.setText(f"2. {glasses_rec[0][0]}" if len(glasses_rec) > 0 else "2. (추천 없음)")
        self.btn_glasses1.setEnabled(len(glasses_rec) > 0)
        self.btn_glasses2.setText(f"3. {glasses_rec[1][0]}" if len(glasses_rec) > 1 else "3. (추천 없음)")
        self.btn_glasses2.setEnabled(len(glasses_rec) > 1)

        selected_type = status["selected_type"]
        self.btn_ar.setEnabled(selected_type == "glasses" and len(glasses_rec) > 0)
        self.btn_ar.setText("안경 벗기 (착용중)" if status["ar_active"] else "안경 써보기 (AR)")

        awaiting = status["awaiting_feedback"]
        self.btn_good.setEnabled(awaiting)
        self.btn_bad.setEnabled(awaiting)

        tags = (result["face_tags"][:1] + result["body_tags"][:1])
        self.tags_label.setText("\n".join(tags) if tags else "")

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
