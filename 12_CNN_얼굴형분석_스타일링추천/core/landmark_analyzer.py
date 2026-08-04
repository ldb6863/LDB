# -*- coding: utf-8 -*-
"""
core/landmark_analyzer.py
=========================
기존 프로젝트의 함수형 인터페이스와 앙상블용 기하 점수를 유지하면서,
팀원 코드의 세부 얼굴 지표/복합 태그 기능을 추가한 통합본입니다.

기존 호환 인터페이스:
    detect_face_and_landmarks(frame_bgr) -> (face_crop, landmarks dict) | (None, None)
    extract_face_metrics(landmarks) -> dict | None
    get_modifier_tags(metrics) -> list[str]
    geometric_class_scores(metrics, gender) -> dict | None

추가 인터페이스:
    extract_detailed_face_metrics(landmarks) -> (metrics dict, tags list)

주의:
- 얼굴형 최종 판정은 기존 CNN+랜드마크 앙상블에서 담당합니다.
- 추가된 상세 태그는 얼굴형을 강제로 덮어쓰지 않고 스타일 추천에만 사용합니다.
"""

import math
import mediapipe as mp

_mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

LEFT_EYE_IDX = 33
RIGHT_EYE_IDX = 263
FOREHEAD_TOP_IDX = 10
CHIN_BOTTOM_IDX = 152
LEFT_TEMPLE_IDX = 162
RIGHT_TEMPLE_IDX = 389
LEFT_JAW_IDX = 132
RIGHT_JAW_IDX = 361
NOSE_TIP_IDX = 1
BROW_MID_IDX = 168
NOSE_BOTTOM_IDX = 2


def detect_face_and_landmarks(frame_bgr):
    """얼굴을 찾아 (crop된 얼굴 이미지, 랜드마크 dict)를 반환합니다."""
    import cv2

    h, w = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = _mp_face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return None, None

    lm = results.multi_face_landmarks[0].landmark

    xs = [int(p.x * w) for p in lm]
    ys = [int(p.y * h) for p in lm]
    x1, x2 = max(min(xs), 0), min(max(xs), w)
    y1, y2 = max(min(ys), 0), min(max(ys), h)

    # 기존 학습/Jetson 입력 형식을 유지하기 위해 crop 방식은 변경하지 않습니다.
    pad = int(0.15 * (x2 - x1))
    x1, x2 = max(x1 - pad, 0), min(x2 + pad, w)
    y1, y2 = max(y1 - pad, 0), min(y2 + pad, h)

    face_crop = frame_bgr[y1:y2, x1:x2]
    if face_crop.size == 0:
        return None, None

    landmarks = {
        "left_eye": (int(lm[LEFT_EYE_IDX].x * w), int(lm[LEFT_EYE_IDX].y * h)),
        "right_eye": (int(lm[RIGHT_EYE_IDX].x * w), int(lm[RIGHT_EYE_IDX].y * h)),
        "forehead_top": (int(lm[FOREHEAD_TOP_IDX].x * w), int(lm[FOREHEAD_TOP_IDX].y * h)),
        "chin_bottom": (int(lm[CHIN_BOTTOM_IDX].x * w), int(lm[CHIN_BOTTOM_IDX].y * h)),
        "left_temple": (int(lm[LEFT_TEMPLE_IDX].x * w), int(lm[LEFT_TEMPLE_IDX].y * h)),
        "right_temple": (int(lm[RIGHT_TEMPLE_IDX].x * w), int(lm[RIGHT_TEMPLE_IDX].y * h)),
        "left_jaw": (int(lm[LEFT_JAW_IDX].x * w), int(lm[LEFT_JAW_IDX].y * h)),
        "right_jaw": (int(lm[RIGHT_JAW_IDX].x * w), int(lm[RIGHT_JAW_IDX].y * h)),
        "nose_tip": (int(lm[NOSE_TIP_IDX].x * w), int(lm[NOSE_TIP_IDX].y * h)),
        "brow_mid": (int(lm[BROW_MID_IDX].x * w), int(lm[BROW_MID_IDX].y * h)),
        "nose_bottom": (int(lm[NOSE_BOTTOM_IDX].x * w), int(lm[NOSE_BOTTOM_IDX].y * h)),
        # 상세 분석에서 z값을 포함한 MediaPipe 원본 좌표가 필요하므로 함께 보관합니다.
        # 기존 함수들은 이 두 내부 키를 사용하지 않아 호환성에 영향이 없습니다.
        "_raw_landmarks": lm,
        "_frame_size": (w, h),
    }
    return face_crop, landmarks


def _dist(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def extract_face_metrics(landmarks):
    """기존 앙상블/추천용 랜드마크 비율을 계산합니다."""
    if not landmarks:
        return None

    eye_dist = _dist(landmarks["left_eye"], landmarks["right_eye"])
    if eye_dist <= 0:
        return None

    face_width = _dist(landmarks["left_temple"], landmarks["right_temple"])
    jaw_width = _dist(landmarks["left_jaw"], landmarks["right_jaw"])
    face_height = _dist(landmarks["forehead_top"], landmarks["chin_bottom"])
    midface = _dist(landmarks["brow_mid"], landmarks["nose_bottom"])
    lowerface = _dist(landmarks["nose_bottom"], landmarks["chin_bottom"])
    midface_ratio = midface / lowerface if lowerface > 0 else None

    return {
        "face_width_ratio": face_width / eye_dist,
        "jaw_width_ratio": jaw_width / eye_dist,
        "face_height_ratio": face_height / eye_dist,
        "midface_ratio": midface_ratio,
        "length_width_ratio": face_height / face_width if face_width > 0 else None,
        "jaw_cheek_ratio": jaw_width / face_width if face_width > 0 else None,
    }


def classify_by_geometry(metrics):
    if metrics is None or metrics.get("length_width_ratio") is None:
        return None, None

    lw = metrics["length_width_ratio"]
    jc = metrics["jaw_cheek_ratio"]

    if lw < 1.15:
        shape = "Square" if jc >= 0.92 else "Round"
    elif lw < 1.3:
        shape = "Square" if jc >= 0.85 else "Oval"
    elif lw < 1.6:
        shape = "Oval"
    else:
        shape = "Rectangle"

    return shape, {"length_width_ratio": lw, "jaw_cheek_ratio": jc}


THRESH_NARROW_TEMPLE = 1.55
THRESH_WIDE_JAW = 1.49
THRESH_LONG_MIDFACE = 0.77


def get_modifier_tags(metrics):
    """기존 DB modifier와 연결되는 영문 태그를 반환합니다."""
    if metrics is None:
        return []
    tags = []
    if metrics["face_width_ratio"] < THRESH_NARROW_TEMPLE:
        tags.append("narrow_temple")
    if metrics["jaw_width_ratio"] > THRESH_WIDE_JAW:
        tags.append("wide_jaw")
    if metrics["midface_ratio"] and metrics["midface_ratio"] > THRESH_LONG_MIDFACE:
        tags.append("long_midface")
    return tags


_GEOMETRIC_CENTROIDS = {
    "men": {
        "Oval": {"jaw_width_ratio": 1.525, "face_height_ratio": 2.073, "midface_ratio": 0.734},
        "Rectangle": {"jaw_width_ratio": 1.500, "face_height_ratio": 1.937, "midface_ratio": 0.749},
        "Round": {"jaw_width_ratio": 1.540, "face_height_ratio": 1.854, "midface_ratio": 0.760},
        "Square": {"jaw_width_ratio": 1.535, "face_height_ratio": 1.892, "midface_ratio": 0.723},
    },
    "women": {
        "Oval": {"jaw_width_ratio": 1.446, "face_height_ratio": 1.813, "midface_ratio": 0.802},
        "Rectangle": {"jaw_width_ratio": 1.476, "face_height_ratio": 1.951, "midface_ratio": 0.791},
        "Round": {"jaw_width_ratio": 1.463, "face_height_ratio": 1.775, "midface_ratio": 0.775},
        "Square": {"jaw_width_ratio": 1.456, "face_height_ratio": 1.794, "midface_ratio": 0.777},
    },
}

_METRIC_STD = {"jaw_width_ratio": 0.06, "face_height_ratio": 0.18, "midface_ratio": 0.09}


def geometric_class_scores(metrics, gender):
    gender_key = {"M": "men", "F": "women", "men": "men", "women": "women"}.get(gender)
    if gender_key is None or metrics is None:
        return None

    raw_scores = {}
    for face_shape, centroid in _GEOMETRIC_CENTROIDS[gender_key].items():
        dist_sq = 0.0
        used = 0
        for key, std in _METRIC_STD.items():
            val = metrics.get(key)
            if val is None:
                continue
            dist_sq += ((val - centroid[key]) / std) ** 2
            used += 1
        if used == 0:
            return None
        raw_scores[face_shape] = math.exp(-dist_sq / 2.0)

    total = sum(raw_scores.values())
    if total <= 0:
        return None
    return {key: value / total for key, value in raw_scores.items()}


# ------------------------------------------------------------------
# 팀원 코드에서 가져온 상세 얼굴 지표/복합 태그
# ------------------------------------------------------------------

def _raw_distance(p1, p2, w, h):
    return math.hypot((p2.x - p1.x) * w, (p2.y - p1.y) * h)


def _raw_angle(p1, p2, p3, w, h):
    x1, y1 = p1.x * w, p1.y * h
    x2, y2 = p2.x * w, p2.y * h
    x3, y3 = p3.x * w, p3.y * h
    angle = math.degrees(math.atan2(y3 - y2, x3 - x2) - math.atan2(y1 - y2, x1 - x2))
    angle = abs(angle)
    return 360 - angle if angle > 180 else angle


def _relative_depth(target, reference, w, face_width):
    depth_diff_px = (reference.z - target.z) * w
    return depth_diff_px / face_width if face_width > 0 else 0.0


def extract_detailed_face_metrics(landmarks):
    """팀원 코드의 세부 안면 지표와 한국어 추천 태그를 계산합니다.

    반환:
        (metrics, tags)

    이 결과는 스타일 추천에만 사용하며 CNN 얼굴형을 덮어쓰지 않습니다.
    """
    if not landmarks:
        return {}, []

    raw = landmarks.get("_raw_landmarks")
    frame_size = landmarks.get("_frame_size")
    if raw is None or frame_size is None:
        return {}, []

    w, h = frame_size
    tags = []
    metrics = {}

    top_head = raw[10]
    chin = raw[152]
    left_cheek = raw[234]
    right_cheek = raw[454]
    glabella = raw[9]
    nose_base = raw[94]
    nose_tip = raw[1]
    lip_top = raw[13]
    lip_bottom = raw[14]
    left_eye_out = raw[33]
    left_eye_in = raw[133]
    left_jaw = raw[132]
    right_jaw = raw[361]

    face_height = _raw_distance(glabella, chin, w, h)
    face_width = _raw_distance(left_cheek, right_cheek, w, h)
    metrics["얼굴 너비(px)"] = face_width
    hw_ratio = face_height / face_width if face_width > 0 else 0
    metrics["가로세로 비율"] = hw_ratio

    if hw_ratio >= 1.5:
        tags.append("긴 얼굴형")
    elif hw_ratio <= 1.2:
        tags.append("짧은/둥근 얼굴형")

    upper_face = _raw_distance(top_head, glabella, w, h)
    mid_face = _raw_distance(glabella, nose_base, w, h)
    lower_face = _raw_distance(nose_base, chin, w, h)

    lower_mid_ratio = lower_face / mid_face if mid_face > 0 else 0
    metrics["중안부 대비 하안부 비율"] = lower_mid_ratio
    if lower_mid_ratio >= 1.15:
        tags.append("하안부가 긴 편 (하관 부각)")
    elif lower_face > 0 and mid_face / lower_face >= 1.15:
        tags.append("중안부가 긴 편 (성숙한 인상)")

    total_face_len = upper_face + mid_face + lower_face
    upper_face_ratio = upper_face / total_face_len if total_face_len > 0 else 0
    metrics["상안부 비율"] = upper_face_ratio
    if upper_face_ratio >= 0.23:
        tags.append("이마가 넓은 편 (앞머리 추천)")
    elif upper_face_ratio <= 0.17:
        tags.append("이마가 좁은 편 (앞머리 없이 노출 추천)")
    else:
        tags.append("이마 비율이 균형 잡힌 편 (앞머리 유무 모두 잘 어울림)")

    eye_width = _raw_distance(left_eye_out, left_eye_in, w, h)
    temple_margin = _raw_distance(left_eye_out, left_cheek, w, h)
    temple_ratio = temple_margin / eye_width if eye_width > 0 else 0
    metrics["관자놀이 여백 비율"] = temple_ratio
    if temple_ratio >= 1.5:
        tags.append("넓은 관자놀이 여백 (사이드뱅 추천)")

    philtrum = _raw_distance(nose_base, lip_top, w, h)
    lower_chin = _raw_distance(lip_bottom, chin, w, h)
    philtrum_ratio = philtrum / lower_chin if lower_chin > 0 else 0
    metrics["인중 길이 비율"] = philtrum_ratio
    if philtrum_ratio >= 0.66:
        tags.append("긴 인중")

    jaw_angle = _raw_angle(left_cheek, left_jaw, chin, w, h)
    metrics["턱선 각도"] = jaw_angle
    if jaw_angle <= 115:
        tags.append("각진 턱 (사각턱 특징)")
    elif jaw_angle >= 150:
        tags.append("뾰족한 턱 (V라인)")

    jaw_width = _raw_distance(left_jaw, right_jaw, w, h)
    jaw_width_ratio = jaw_width / face_width if face_width > 0 else 0
    metrics["하관 너비 비율"] = jaw_width_ratio
    if jaw_width_ratio >= 0.8:
        tags.append("넓은 하관 (안정적인 형태)")
    elif jaw_width_ratio <= 0.65:
        tags.append("좁은 하관")

    left_depth = _relative_depth(left_cheek, nose_tip, w, face_width)
    right_depth = _relative_depth(right_cheek, nose_tip, w, face_width)
    cheek_protrusion = (left_depth + right_depth) / 2.0
    metrics["광대 돌출도"] = cheek_protrusion
    if cheek_protrusion >= -0.15:
        tags.append("돌출된 광대 (입체적인 인상)")
    elif cheek_protrusion <= -0.35:
        tags.append("완만한 광대 (부드러운 인상)")

    combo_tags = []
    if "하안부가 긴 편 (하관 부각)" in tags and "각진 턱 (사각턱 특징)" in tags:
        combo_tags.append("중안부/하안부가 발달해 이목구비가 또렷하고 각진 인상")
    if "중안부가 긴 편 (성숙한 인상)" in tags and "뾰족한 턱 (V라인)" in tags:
        combo_tags.append("중안부가 길고 턱선이 갸름해 세련되고 성숙한 인상")
    if "돌출된 광대 (입체적인 인상)" in tags and "넓은 하관 (안정적인 형태)" in tags:
        combo_tags.append("골격이 뚜렷하고 입체적인 강한 인상")
    if "완만한 광대 (부드러운 인상)" in tags and "좁은 하관" in tags:
        combo_tags.append("골격이 완만하고 부드러운 동안 인상")
    if "넓은 관자놀이 여백 (사이드뱅 추천)" in tags and "뾰족한 턱 (V라인)" in tags:
        combo_tags.append("이마가 넓고 턱이 갸름한 하트형 골격")
    if "긴 인중" in tags and "중안부가 긴 편 (성숙한 인상)" in tags:
        combo_tags.append("인중과 중안부가 모두 길어 차분하고 성숙한 인상")

    tags.extend(combo_tags)
    return metrics, tags


def debug_visualize_landmarks():
    import cv2

    targets = {
        "Left Temple": LEFT_TEMPLE_IDX,
        "Right Temple": RIGHT_TEMPLE_IDX,
        "Chin": CHIN_BOTTOM_IDX,
        "Left Jaw": LEFT_JAW_IDX,
        "Right Jaw": RIGHT_JAW_IDX,
        "Mid Between Eyes": BROW_MID_IDX,
        "Forehead Top": FOREHEAD_TOP_IDX,
        "Nose Tip": NOSE_TIP_IDX,
        "Nose Bottom": NOSE_BOTTOM_IDX,
    }

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("웹캠을 찾을 수 없습니다.")
        return

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = _mp_face_mesh.process(rgb)
        if results.multi_face_landmarks:
            h, w = image.shape[:2]
            raw = results.multi_face_landmarks[0].landmark
            for name, index in targets.items():
                point = raw[index]
                cx, cy = int(point.x * w), int(point.y * h)
                cv2.circle(image, (cx, cy), 5, (0, 0, 255), -1)
                cv2.putText(image, f"{name}({index})", (cx + 10, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imshow("Landmark Verification - ESC", image)
        if cv2.waitKey(5) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    debug_visualize_landmarks()
