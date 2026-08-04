# -*- coding: utf-8 -*-
"""얼굴형 + 상세 얼굴 태그 + 상체 태그를 종합해 항목별 스타일링을 추천합니다."""

import math
from collections import Counter


def get_bangs_recommendation(tags):
    if "이마가 넓은 편 (앞머리 추천)" in tags:
        return "O (넓은 이마를 보완하는 앞머리 추천)"
    if "긴 얼굴형" in tags:
        return "O (세로 길이를 분산하는 앞머리 추천)"
    if "이마가 좁은 편 (앞머리 없이 노출 추천)" in tags:
        return "X (이마 노출 또는 업스타일 추천)"
    if "이마 비율이 균형 잡힌 편 (앞머리 유무 모두 잘 어울림)" in tags:
        return "O/X 모두 가능 (취향에 따라 선택)"
    return "△ (앞머리 유무의 영향이 크지 않음)"


def build_full_recommendation(gender, face_shape, face_tags, body_tags):
    """팀원 코드의 항목별 추천 방식을 기존 4클래스 결과에 연결합니다."""
    gender_key = "m" if gender in ("M", "m", "men") else "w"
    shape_key = (face_shape or "").lower()

    result = {
        "기본 컷": None,
        "볼륨 위치": None,
        "기장": None,
        "앞머리": None,
        "유의사항": [],
        "세부 인상": [],
    }

    base_cut = {
        "m": {
            "oval": "가르마 펌 / 댄디컷",
            "round": "리젠트 컷 / 포마드 스타일",
            "square": "크롭컷 / 아이비리그 컷",
            "rectangle": "쉐도우 펌 / 스왈로 펌",
        },
        "w": {
            "oval": "레이어드 컷",
            "round": "단발 태슬컷",
            "square": "히피펌 / 중단발 레이어드",
            "rectangle": "레이어드 웨이브",
        },
    }

    for key, value in base_cut[gender_key].items():
        if key in shape_key:
            result["기본 컷"] = value
            break
    if result["기본 컷"] is None:
        result["기본 컷"] = "자연스러운 텍스처 펌 / 레이어드 컷"

    if "각진 턱 (사각턱 특징)" in face_tags and "넓은 하관 (안정적인 형태)" in face_tags:
        result["볼륨 위치"] = "정수리~중간 볼륨 강조 (턱선 존재감 분산)"
    elif "돌출된 광대 (입체적인 인상)" in face_tags:
        result["볼륨 위치"] = "옆볼륨 최소화, 정수리 볼륨 위주 (광대 강조 완화)"
    elif "완만한 광대 (부드러운 인상)" in face_tags:
        result["볼륨 위치"] = "옆볼륨을 살려 입체감 보완"
    elif "좁은 하관" in face_tags:
        result["볼륨 위치"] = "끝머리·하단 볼륨 강조 (갸름한 하관 보완)"
    else:
        result["볼륨 위치"] = "전체적으로 균등한 볼륨"

    if "목이 짧은 편 (기장으로 라인 보완 추천)" in body_tags:
        result["기장"] = "장발/중단발 이상 (짧은 목 라인 보완)"
    elif "어깨가 넓은 편 (여유 있는 기장/볼륨 추천)" in body_tags:
        result["기장"] = "장발 또는 볼륨감 있는 중단발 (어깨와 밸런스)"
    elif "어깨가 좁은 편 (볼륨감 있는 스타일로 밸런스 추천)" in body_tags:
        result["기장"] = "단발~중단발 + 볼륨 펌 (좁은 어깨 보완)"
    elif "목이 긴 편 (다양한 기장 소화 가능)" in body_tags:
        result["기장"] = "숏컷부터 장발까지 폭넓게 선택 가능"
    else:
        result["기장"] = "중간 기장 중심의 무난한 밸런스"

    result["앞머리"] = get_bangs_recommendation(face_tags)

    if "좌우 어깨 높이차가 있는 편" in body_tags:
        result["유의사항"].append("촬영·스타일링 시 정면 자세와 좌우 밸런스 확인")
    if "긴 인중" in face_tags:
        result["유의사항"].append("인중이 긴 편이므로 과도한 정수리 높이는 피하는 방향 권장")
    if "넓은 관자놀이 여백 (사이드뱅 추천)" in face_tags:
        result["유의사항"].append("사이드뱅 또는 옆머리로 관자놀이 여백 보완")

    combo_phrases = [
        "중안부/하안부가 발달해 이목구비가 또렷하고 각진 인상",
        "중안부가 길고 턱선이 갸름해 세련되고 성숙한 인상",
        "골격이 뚜렷하고 입체적인 강한 인상",
        "골격이 완만하고 부드러운 동안 인상",
        "이마가 넓고 턱이 갸름한 하트형 골격",
        "인중과 중안부가 모두 길어 차분하고 성숙한 인상",
    ]
    result["세부 인상"] = [tag for tag in face_tags if tag in combo_phrases]
    return result


def reliable_tags(counter, sample_count, min_ratio=0.35, min_count=2):
    """스캔 동안 반복 검출된 태그만 최종 특징으로 채택합니다."""
    if sample_count <= 0:
        return []
    threshold = max(min_count, int(math.ceil(sample_count * min_ratio)))
    return [tag for tag, count in counter.most_common() if count >= threshold]


def print_final_report(gender, face_shape, confidence, recommendation,
                       face_tags, body_tags, scan_seconds, method_counts=None):
    gender_text = "남성" if gender in ("M", "m", "men") else "여성"
    print("\n" + "=" * 62)
    print("✨ 얼굴형 + 세부 얼굴 비율 + 상체 비율 종합 분석 완료 ✨")
    print("=" * 62)
    print(f"▶ 선택한 성별: {gender_text}")
    print(f"▶ 최종 얼굴형: {face_shape} ({confidence:.1f}%, {scan_seconds}초 누적 스캔)")
    if method_counts:
        method_text = ", ".join(f"{key}:{value}회" for key, value in method_counts.items())
        print(f"▶ 판정 방식: {method_text}")

    print("\n💇 세부 스타일링 추천")
    print(f"   - 기본 컷   : {recommendation['기본 컷']}")
    print(f"   - 볼륨 위치 : {recommendation['볼륨 위치']}")
    print(f"   - 기장      : {recommendation['기장']}")
    print(f"   - 앞머리    : {recommendation['앞머리']}")

    if recommendation["세부 인상"]:
        print("   - 세부 인상  :")
        for item in recommendation["세부 인상"]:
            print(f"       · {item}")

    if recommendation["유의사항"]:
        print("   - 유의사항  :")
        for note in recommendation["유의사항"]:
            print(f"       · {note}")

    print("\n🏷️ 반복 검출된 얼굴 특징")
    if face_tags:
        for tag in face_tags:
            print(f"   - {tag}")
    else:
        print("   - 뚜렷한 추가 특징 없음")

    print("\n🧍 상체 실루엣 참고")
    if body_tags:
        for tag in body_tags:
            print(f"   - {tag}")
    else:
        print("   - 뚜렷한 특징 없음 또는 어깨 인식 부족")
    print("=" * 62 + "\n")
