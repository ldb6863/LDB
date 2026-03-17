FPGA 기반 임베디드 전자레인지 시스템 설계FSM을 활용한 하드웨어 통합 제어 및 PWM 정밀 구동 실현 

1. 프로젝트 개요 (Project Introduction)
  주제: Xilinx Artix-7(Basys3) FPGA를 활용한 임베디드 전자레인지 시스템 설계 
  목표: FSM(Finite State Machine)을 활용하여 대기, 조리, 일시정지, 완료 상태의 유기적 제어 로직 설계 
        DC·서보 모터, 부저, FND 등 이기종 하드웨어 인터페이스 통합 및 PWM 정밀 제어 
        도어 감지 안전 로직 및 버튼 디바운싱 처리를 통한 시스템 신뢰성 확보

2. 시스템 사양 (System Specifications)
  Platform: Xilinx Artix-7 (Basys3 Board) 
  Toolchain: Vivado Design Suite 2021.1 
  Clock Speed: 100MHz (10ns Period) 
  인터페이스: 4-Digit 7-Segment, 16-bit LED, DC Motor, Servo Motor, Buzzer

3. 핵심 설계 및 기능 (System Design) 
  Finite State Machine (FSM) 
  시스템의 안정성을 위해 모든 상태를 4가지 메인 상태로 정의하고 중앙 집중식 제어 로직을 구현했습니다.
  IDLE: 조리 대기 및 타이머 설정 상태 
  COOK: 조리 가동 상태 (DC 모터, 타이머, LED 시프트 활성화) 
  PAUSE: 조리 일시정지 및 도어 오픈 시 즉시 진입하는 안전 상태 
  FINISH: 조리 완료 알림 및 멜로디 출력 상태
  주요 서브모듈 구현 
  
  Timer & FND: BCD 기반 카운트다운 로직 및 1ms 스캔 주기 기반의 7-Segment 표시 제어 
  Actuator Control: * 70% Duty Cycle 고정 PWM을 이용한 DC 모터 속도 제어 50Hz 주기 
    - PWM을 이용한 도어 개폐용 서보 모터 제어 (0° ~ 90°) 
    - 상태별 가변 주파수 사각파를 이용한 부저 멜로디 연주
    
<img width="801" height="582" alt="image" src="https://github.com/user-attachments/assets/003718af-e0ee-4d12-acd1-d83563581e70" />
<img width="1092" height="773" alt="image" src="https://github.com/user-attachments/assets/fc626a1b-94ac-4a3b-a932-86c1163be215" />


  
  
4. 트러블슈팅 (Trouble-shooting)
설계 과정에서 발생한 문제를 논리적으로 해결하며 시스템 완성도를 높였습니다.
버튼 입력 불안정 해결: 레벨 트리거 방식의 입력 오류를 해결하기 위해 모든 버튼 입력에 엣지 검출(Edge Detection) 로직을 추가하여 신뢰성을 확보했습니다.
모듈 간 동기화 이슈: FSM과 타이머 모듈이 독립적으로 동작하여 발생하던 상태 꼬임 문제를 해결하기 위해, 모든 동작 트리거를 FSM으로 집중시켜 중앙 제어 방식으로 구조를 개선했습니다.

5. 검증 결과 (Test-bench & Result)
  시뮬레이션: Vivado Simulator를 사용하여 시간 설정, 시작/정지, 도어 안전 로직 등 총 9단계 시나리오 검증 완료 
  파라미터 최적화: 실제 하드웨어 주기를 시뮬레이션용 파라미터로 가변 설계하여 검증 효율성 증대 
