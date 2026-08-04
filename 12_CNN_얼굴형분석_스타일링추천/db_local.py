# -*- coding: utf-8 -*-
"""
db_local.py
===========
Jetson 안 SQLite 파일 하나로 모든 걸 관리합니다 (서버 불필요).

v3(하이브리드) 변경 사항:
- 추천을 "얼굴형별 고정 리스트"에서 "기본 기장(base) + 디테일 수식어(modifier)
  모듈형 조합"으로 바꿨습니다. (팀원 방식 반영)
- 성별(gender)에 따라 기본 기장 후보가 달라집니다.
- 판정 로그에 만족도 피드백(feedback) 컬럼 추가, 얼굴 사진 자체는 저장하지 않습니다.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "faceshape.db")

# ------------------------------------------------------------------
# 시드 데이터
# ------------------------------------------------------------------

# 1) 기본 기장 (성별 x 얼굴형 별로 1순위 후보)
_BASE_STYLE_SEED = [
    # (gender, face_shape, style_name, reason)
    ("F", "Round",  "중단발 레이어드",   "세로 라인을 강조해 둥근 인상을 갸름하게 보완"),
    ("F", "Square", "긴 머리 웨이브",    "부드러운 곡선으로 각진 턱선을 완화"),
    ("F", "Oval",   "숏컷",             "대부분의 스타일이 잘 어울리는 균형 잡힌 골격"),
    ("F", "Rectangle", "긴 생머리",         "세로로 긴 얼굴에 안정감을 더함"),
    ("M", "Round",  "드롭컷(숏기장)",    "정수리 볼륨으로 세로 라인 강조"),
    ("M", "Square", "가일컷(미디움 깐머리)", "이마를 드러내 각진 턱선과 균형"),
    ("M", "Oval",   "댄디컷",           "대부분의 스타일이 잘 어울리는 균형 잡힌 골격"),
    ("M", "Rectangle", "상고 커트",         "뒷볼륨으로 세로 길이감 분산"),
]

# 2) 디테일 수식어 (get_modifier_tags()가 뽑아내는 태그와 매칭)
_MODIFIER_SEED = [
    # (tag, gender, modifier_name, reason)
    ("narrow_temple", "F", "사이드뱅",       "관자놀이 여백을 가려 얼굴 폭 보완"),
    ("narrow_temple", "M", "옆머리 내림",     "관자놀이 여백을 가려 얼굴 폭 보완"),
    ("wide_jaw",       "F", "다운펌(볼륨 억제)", "옆으로 퍼지지 않게 턱선 각짐을 완화"),
    ("wide_jaw",       "M", "다운펌",          "옆으로 퍼지지 않게 턱선 각짐을 완화"),
    ("long_midface",   "F", "풀뱅",           "중안부 길이를 시각적으로 줄여줌"),
    ("long_midface",   "M", "일자 앞머리",     "중안부 길이를 시각적으로 줄여줌"),
]

# 3) 안경 추천 (기존 유지)
_GLASSES_SEED = [
    ("Round",     "각진 사각 뿔테",     "assets/glasses2.png", 1, "둥근 얼굴에 뚜렷한 직선을 더해 이목구비를 선명하고 세련되게 잡아줌"),
    ("Round",     "하금테(브로우라인)", "assets/glasses3.png", 2, "윗라인을 강조해 시선을 위로 끌어올려 얼굴형 균형"),
    ("Square",    "완전한 원형 테",     "assets/glasses5.png", 1, "각진 턱선의 느낌을 곡선으로 중화시켜 인상을 부드럽게 함"),
    ("Square",    "베이직 웰링턴 테",   "assets/glasses0.png", 2, "무난한 곡선으로 각진 느낌을 자연스럽게 완화"),
    ("Oval",      "베이직 웰링턴 테",   "assets/glasses0.png", 1, "균형 잡힌 골격이라 대부분의 프레임이 잘 어울림"),
    ("Oval",      "그라데이션 상단강조테", "assets/glasses1.png", 2, "개성 있는 포인트를 주고 싶을 때 추천"),
    ("Rectangle", "하금테(브로우라인)", "assets/glasses3.png", 1, "상단에 포인트를 줘서 세로 길이를 시각적으로 분할"),
    ("Rectangle", "가로형 스퀘어 테",   "assets/glasses4.png", 2, "가로 라인을 더해 세로로 긴 비율을 시원하게 보완"),
]


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_styles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gender TEXT NOT NULL,       -- 'M' or 'F'
            face_shape TEXT NOT NULL,
            style_name TEXT NOT NULL,
            reason TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS modifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT NOT NULL,          -- extract 'narrow_temple' 등 core.get_modifier_tags() 결과와 매칭
            gender TEXT NOT NULL,
            modifier_name TEXT NOT NULL,
            reason TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS glasses_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            face_shape TEXT NOT NULL,
            item_name TEXT NOT NULL,
            image_path TEXT,
            priority INTEGER NOT NULL,
            reason TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP,
            gender TEXT,
            face_shape TEXT NOT NULL,
            confidence REAL NOT NULL,
            modifier_tags TEXT,          -- 콤마로 구분된 태그 (예: 'narrow_temple,wide_jaw')
            selected_type TEXT,          -- 'hair' or 'glasses'
            selected_item TEXT,
            feedback TEXT                -- 'good' / 'bad' / NULL(응답 없음)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM base_styles")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO base_styles (gender, face_shape, style_name, reason) VALUES (?, ?, ?, ?)",
            _BASE_STYLE_SEED,
        )
    cur.execute("SELECT COUNT(*) FROM modifiers")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO modifiers (tag, gender, modifier_name, reason) VALUES (?, ?, ?, ?)",
            _MODIFIER_SEED,
        )
    cur.execute("SELECT COUNT(*) FROM glasses_recommendations")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO glasses_recommendations (face_shape, item_name, image_path, priority, reason) "
            "VALUES (?, ?, ?, ?, ?)",
            _GLASSES_SEED,
        )
    conn.commit()
    conn.close()


def get_hair_recommendation(gender, face_shape, modifier_tags):
    """성별+얼굴형 -> 기본 기장 1개 + 해당되는 수식어들을 조합해서 반환.

    반환 예: {
        "base": ("중단발 레이어드", "세로 라인을 강조해..."),
        "modifiers": [("사이드뱅", "관자놀이 여백을..."), ...]
    }
    """
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT style_name, reason FROM base_styles WHERE gender=? AND face_shape=? LIMIT 1",
        (gender, face_shape),
    )
    base = cur.fetchone()

    modifiers = []
    for tag in modifier_tags:
        cur.execute(
            "SELECT modifier_name, reason FROM modifiers WHERE tag=? AND gender=?",
            (tag, gender),
        )
        row = cur.fetchone()
        if row:
            modifiers.append(row)
    conn.close()
    return {"base": base, "modifiers": modifiers}


def get_glasses_recommendation(face_shape):
    """얼굴형 -> [(item_name, image_path, reason), ...] priority 순"""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT item_name, image_path, reason FROM glasses_recommendations "
        "WHERE face_shape=? ORDER BY priority ASC",
        (face_shape,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def insert_log(gender, face_shape, confidence, modifier_tags,
                selected_type=None, selected_item=None, feedback=None):
    conn = _connect()
    conn.execute(
        "INSERT INTO detection_log "
        "(gender, face_shape, confidence, modifier_tags, selected_type, selected_item, feedback) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (gender, face_shape, confidence, ",".join(modifier_tags), selected_type, selected_item, feedback),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(get_hair_recommendation("F", "Round", ["narrow_temple"]))
    print(get_glasses_recommendation("Round"))