# FPGA 기반 임베디드 전자레인지 시스템 설계
> **FSM을 활용한 하드웨어 통합 제어 및 PWM 정밀 구동 실현**

## 1. 프로젝트 개요 (Project Introduction)
* **주제:** Xilinx Artix-7(Basys3) FPGA를 활용한 임베디드 전자레인지 시스템 설계
* **목표:**
    * FSM(Finite State Machine)을 활용하여 대기, 조리, 일시정지, 완료 상태의 유기적 제어 로직 설계
    * DC·서보 모터, 부저, FND 등 이기종 하드웨어 인터페이스 통합 및 PWM 정밀 제어
    * 조리 중 문 열림 감지 시 즉시 중단되는 안전 로직과 버튼 디바운싱을 통한 시스템 신뢰성 확보

## 2. 시스템 사양 (System Specifications)
| Specs | Details |
| :--- | :--- |
| **Platform** | Xilinx Artix-7 (Basys3) |
| **Clock Speed** | 100MHz (10ns Period) |
| **Input** | Reset SW, Push Buttons |
| **Output** | 4-Digit 7-Segment, LED, DC Motor, Servo Motor, Buzzer |
| **Toolchain** | Vivado Design 2021.1 |

## 3. 핵심 설계 및 기능 (System Design)
### Finite State Machine (FSM)
시스템의 안정성을 위해 상태 변화를 정의하고 중앙 집중식 제어 로직을 구현했습니다.
* **IDLE (2'b00):** 초기 상태 및 조리 대기. 모든 모터가 정지하며 타이머 설정값 유지
* **COOK (2'b01):** 조리 가동 상태. DC 모터, 타이머, LED 시프트 동시 활성화
* **PAUSE (2'b10):** 조리 중 정지 버튼 입력 또는 문 열릴 시 진입하는 안전 상태
* **FINISH (2'b11):** 조리 완료 상태. 완료 멜로디 출력 및 FND 점멸 후 IDLE 복귀

<img width="801" height="582" alt="image" src="https://github.com/user-attachments/assets/003718af-e0ee-4d12-acd1-d83563581e70" />

<img width="1092" height="773" alt="image" src="https://github.com/user-attachments/assets/fc626a1b-94ac-4a3b-a932-86c1163be215" />

### 주요 모듈 구현 특징
* **Timer & FND:** 1초 주기의 카운트다운 기준 신호를 생성하고 BCD 기반 시간 데이터(분/초)를 표시
* **DC Motor Control:** 70% Duty Cycle의 PWM 신호를 생성하여 회전판 속도 제어
* **Servo Motor Control:** 50Hz 주기 기반의 PWM으로 도어 개폐 각도(0°~90°) 제어 및 진동 방지 로직 적용
* **Melody Player:** 시작/일시정지/완료/문 열림 등 상태별 시나리오에 따른 가변 주파수 연주

## 4. 트러블슈팅 (Trouble-shooting)
* **버튼 엣지 검출 (Edge Detection):** 레벨 트리거 방식에서 발생하는 중복 입력 오류를 해결하기 위해 상승 엣지(Positive Edge) 검출 코드를 적용하여 버튼 조작의 정확도를 높임
* **타이머-FSM 동기화:** 독립적으로 동작하던 타이머 로직을 FSM의 `timer_en` 신호에 강제 동기화시켜 일시정지 및 재개 시의 싱크 오류를 해결
* **중앙 집중식 제어 구조:** 모든 입력(버튼, 센서 등)을 FSM으로 집중시켜 코드 수정 범위를 축소하고 시스템 안정성 확보

## 5. 검증 결과 (Test-bench & Result)
* **테스트벤치 시나리오:** 시간 설정(10초~1분), 조리 중 취소, 문 열림 강제 중단 등 총 9가지 예외 상황 검증 완료
* **파라미터 최적화:** 시뮬레이션 속도 향상을 위해 하드웨어 카운트 값을 시뮬레이션용으로 가변 설계하여 검증 효율 증대

---
**작성일:** 2026. 03. 02
**개발자:** 이경한, 이동빈

