<div align="center">

# 이동빈

### Semiconductor IC · FPGA · Embedded Systems

[![GitHub](https://img.shields.io/badge/GitHub-ldb6863-181717?style=flat-square&logo=github)](https://github.com/ldb6863)
[![Repository](https://img.shields.io/badge/Repository-LDB-181717?style=flat-square&logo=github)](https://github.com/ldb6863/LDB)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=flat-square&logo=gmail&logoColor=white)](mailto:ldb6863@gmail.com)

</div>

---

## Education

**세종대학교 전자정보통신공학과**  
2018.03 – 2025.02

---

## Training

### AI 시스템반도체 SW 개발자

- FPGA(Xilinx Artix-7) 기반 임베디드 시스템 설계
- Verilog/SystemVerilog RTL 설계 및 FSM 구현
- STM32·Arduino·Raspberry Pi 연동 IoT 시스템 통합
- 교육기관: 대한상공회의소

### 차량용 반도체 IC 설계

- Cadence Virtuoso 기반 아날로그·디지털 IC 설계
- Full-custom IC 및 PCell/TEG 설계
- SRAM·Display Driver IC 설계 프로젝트 수행
- 교육기관: 렛유인에듀

---

## Tech Stack

### IC Design

![Cadence](https://img.shields.io/badge/Cadence_Virtuoso-FF0000?style=flat-square)
![Spectre](https://img.shields.io/badge/Spectre-Simulation-8B0000?style=flat-square)
![Assura](https://img.shields.io/badge/Assura-DRC%2FLVS-B22222?style=flat-square)
![SKILL](https://img.shields.io/badge/SKILL-PCell-8A2BE2?style=flat-square)

### FPGA & RTL

![Verilog](https://img.shields.io/badge/Verilog-4B0082?style=flat-square)
![SystemVerilog](https://img.shields.io/badge/SystemVerilog-6B3FA0?style=flat-square)
![Vivado](https://img.shields.io/badge/Xilinx_Vivado-E01F27?style=flat-square&logo=amd&logoColor=white)
![Artix-7](https://img.shields.io/badge/Xilinx_Artix--7-E01F27?style=flat-square&logo=amd&logoColor=white)

### Embedded

![C](https://img.shields.io/badge/C-A8B9CC?style=flat-square&logo=c&logoColor=black)
![C++](https://img.shields.io/badge/C++-00599C?style=flat-square&logo=cplusplus&logoColor=white)
![STM32](https://img.shields.io/badge/STM32-03234B?style=flat-square&logo=stmicroelectronics&logoColor=white)
![Arduino](https://img.shields.io/badge/Arduino-00878F?style=flat-square&logo=arduino&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-A22846?style=flat-square&logo=raspberrypi&logoColor=white)
![FreeRTOS](https://img.shields.io/badge/FreeRTOS-00A4A6?style=flat-square)
![Qt](https://img.shields.io/badge/Qt-41CD52?style=flat-square&logo=qt&logoColor=white)
![MariaDB](https://img.shields.io/badge/MariaDB-003545?style=flat-square&logo=mariadb&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat-square&logo=github&logoColor=white)

---

## Projects

### IC Design

| No. | 프로젝트 | 담당 역할 | 사용 기술 |
|---:|---|---|---|
| 1 | **8x8 SRAM Design (64-bit Asynchronous SRAM)** | Decoder / Pre-charge Circuit / Write Driver 설계 | Cadence Virtuoso, Spectre, ADE, Assura, GPDK 90nm |
| 2 | **2-stage High-speed Comparator** | 90nm/180nm NMOS·PMOS Input Pair 회로 설계 및 시뮬레이션 분석 참여 | Cadence Virtuoso, Spectre, GPDK 90nm/180nm |
| 3 | **2-stage OP-AMP** | NMOS/PMOS Input Pair 회로 설계 및 Process Corner별 특성 분석 참여 | Cadence Virtuoso, Spectre, GPDK 90nm/180nm |
| 4 | **Repeater Design & PPA Analysis** | Repeater 설계 및 PPA 특성 분석 참여 | Cadence Virtuoso, Spectre |
| 5 | **Large Panel Source Drive IC: Design Rules & Layout** | Source Drive IC 회로 블록 분석 및 Design Rule 작성 참여 | Cadence Virtuoso |
| 6 | **Full-custom Digital IC: MAC Unit** | 8-bit Register, 11-bit Register 설계 | Cadence Virtuoso, Spectre |
| 7 | **TEG Design Using PCell** | MIM Capacitor, Pad PCell 설계 및 발표 | Cadence Virtuoso, SKILL, GPDK |

### FPGA & Embedded Systems

| No. | 프로젝트 | 담당 역할 | 사용 기술 |
|---:|---|---|---|
| 8 | **FPGA 기반 임베디드 전자레인지 시스템** | FSM·타이머·모터 제어 로직 설계 및 통합 구현 참여 | Verilog, Xilinx Vivado 2021.1, Xilinx Artix-7 |
| 9 | **FPGA 기반 스마트 공조기 시스템** | RTC FSM, DS1302 FSM, 3-wire 통신, UART·로터리 인코더 기반 시간 설정 로직 구현 | Verilog, Xilinx Vivado 2021.1, Xilinx Artix-7 |
| 10 | **IoT 기반 무인 도서 반납 키오스크** | STM32 키오스크·Arduino 반납기 설계 및 통합 구현 참여 | STM32F4/L4, Arduino Uno, ESP8266, HC-06, RC522, Raspberry Pi, MariaDB, TCP Socket |
| 11 | **물류 자동 분류 시스템** | HX711 무게 측정 및 5단계 필터 파이프라인 설계, 로드셀 케이스 3D 설계 | STM32 Nucleo F411RE, FreeRTOS, C/C++, Git/GitHub |
| 12 | **CNN 기반 얼굴형 분석 및 스타일링 추천 시스템** | CNN 얼굴형 분류, 데이터 준비, 모델 학습, 성능 개선, Jetson Nano 배포 검증 | Jetson Nano, TensorFlow 2.4.1, MobileNetV2, OpenCV, MediaPipe, SQLite, PyQt5 |

---


<div align="center">

**Email:** ldb6863@gmail.com

</div>
