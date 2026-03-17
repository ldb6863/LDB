# FPGA 기반 스마트 공조 시스템 (Smart HVAC System)
> **Master FSM 기반의 온습도 임계값 설정 및 자동 제어 로직 구현**

## 1. 프로젝트 개요 (Project Introduction)
* **주제:** FPGA를 활용한 실시간 온습도 모니터링 및 액추에이터 자동 제어 시스템 설계
* **목표:**
    * DHT11 센서 데이터를 수집하여 현재 온습도와 설정된 임계값에 따른 실시간 제어
    * Master FSM을 통한 시스템 상태 관리 및 버튼 입력을 활용한 인터랙티브 설정 기능 구현
    * 냉방(DC 모터) 및 제습(서보 모터) 구동을 통한 스마트 환경 제어 실현

## 2. 시스템 사양 (System Specifications)
| Specs | Details |
| :--- | :--- |
| **Platform** | Xilinx Artix-7 (Basys3) |
| **Clock Speed** | 100MHz (10ns Period) |
| **Sensor** | DHT11 (Temperature & Humidity) |
| **Output Interface** | 4-Digit 7-Segment, DC Motor, Servo Motor, LED, Buzzer |
| **Toolchain** | Vivado Design 2021.1 |

## 3. 핵심 설계 및 기능 (System Design)
### Master Finite State Machine (Master FSM)
시스템의 모든 동작은 아래 4가지 Master 상태를 중심으로 제어됩니다.
* **IDLE (2'b00):** 초기 리셋 상태. 모든 동작이 정지된 대기 상태
* **TEMP_SET (2'b01):** 온도 임계값(Target Temp)을 설정하는 상태. FND에 설정값이 표시됨
* **HUMI_SET (2'b10):** 습도 임계값(Target Humi)을 설정하는 상태. FND에 설정값이 표시됨
* **RUN (2'b11):** 실제 센서 데이터와 임계값을 비교하여 DC 모터 및 서보 모터를 구동하는 가동 상태

### 주요 모듈 구현 특징
* **DHT11 Controller:** 1-Wire 프로토콜을 구현하여 40-bit 데이터를 수신하고, 유효한 데이터인지 체크섬으로 검증
* **Threshold Control:** 버튼 입력(UP/DOWN)에 따라 온도/습도 설정값을 변경하며, 설정 완료 시 다음 상태로 전이
* **PWM Actuator Control:**
    * **냉방:** 현재 온도가 설정값보다 높을 때 DC 모터를 가동하여 냉방 수행
    * **제습:** 현재 습도가 설정값보다 높을 때 서보 모터를 회전시켜 제습 수행
* **FND Display:** Master FSM의 상태에 따라 현재 데이터와 설정 데이터(Target)를 구분하여 출력

## 4. 트러블슈팅 (Trouble-shooting)
PDF에 기록된 실제 기술적 문제 해결 사례입니다.

* **FND 데이터 고정 및 갱신 오류:** FND가 항상 현재 온습도만 표시하여 설정값을 확인하기 어려웠던 문제. -> Master FSM의 상태(TEMP_SET, HUMI_SET)와 연동하여 **설정 모드 시 설정값이 출력되도록 출력 로직을 분기**하여 해결
* **FSM 상태 전이 안정성 확보:** 상태 전환 시 버튼 입력이 중복되거나 무시되는 현상 발생. -> 모든 제어 버튼에 **상승 엣지 검출(Positive Edge Detection)** 로직을 추가하여 한 번의 클릭에 정확히 한 단계씩 상태가 변하도록 개선
* **모듈 간 신호 충돌 방지:** 여러 모듈이 동시에 출력 포트를 제어하려 할 때 발생하는 데이터 꼬임 현상. -> 모든 실행 명령을 **Master FSM의 제어 신호(Enable)에 종속**시켜 동작 우선순위를 명확히 함

## 5. 검증 결과 (Test-bench & Result)
* **Master FSM 시뮬레이션:** IDLE -> TEMP_SET -> HUMI_SET -> RUN으로 이어지는 상태 전이 시나리오 검증
* **임계값 비교 로직:** 센서 데이터가 설정치를 초과하는 순간 정확히 PWM 신호가 발생하는지 파형 분석 완료

---
**작성일:** 2026. 03. 17
**개발자:** 이경한, 이동빈
