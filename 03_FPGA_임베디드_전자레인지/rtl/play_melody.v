`timescale 1ns / 1ps

module play_melody(
    input clk,               // 100MHz
    input reset,
    input [2:0] melody_sel,  // FSM에서 주는 신호 (0:IDLE, 1:START, 2:PAUSE, 3:FINISH)
    output reg buzzer
    );

    // --- 주파수 설정 (반주기 카운트값) ---
    localparam DO  = 22'd191_112; // C4 (261Hz)
    localparam MI  = 22'd151_686; // E4 (329Hz)
    localparam SOL = 22'd127_551; // G4 (392Hz)
    localparam SI  = 22'd101_419; // B4 (493Hz)
    localparam HIGH_DO = 22'd95_556; // C5 (523Hz)

    // --- 시간 제어 설정 ---
    localparam TIME_100MS = 10_000_000; // 음 하나당 재생 시간

    // --- 상태 및 카운터 ---
    reg [2:0]  r_state;         // 시퀀스 내의 음계 순서
    reg [23:0] r_time_cnt;      // 음 재생 시간 카운터
    reg [21:0] r_freq_cnt;      // 주파수 생성 카운터
    reg [21:0] r_max_cnt;       // 현재 선택된 주파수 값
    reg [2:0]  r_last_sel;      // 이전 melody_sel 저장 (엣지 체크용)
    reg        r_busy;          // 현재 멜로디 연주 중

    // 1. 멜로디 시퀀스 정의 (melody_sel에 따른 음 분기)
    always @(*) begin
        r_max_cnt = 0;
        case (melody_sel)
            3'd1: begin // [조리 시작/진행] 도-미-솔 상행선 (반복 없이 시작 시 1회 권장)
                case (r_state)
                    1: r_max_cnt = DO;
                    2: r_max_cnt = MI;
                    3: r_max_cnt = SOL;
                    default: r_max_cnt = 0;
                endcase
            end
            3'd2: begin // [일시정지] 솔-미 짧게 (경고)
                case (r_state)
                    1: r_max_cnt = SOL;
                    2: r_max_cnt = MI;
                    default: r_max_cnt = 0;
                endcase
            end
            3'd3: begin // [조리 완료] 삐- 삐- 삐- (고음 반복)
                case (r_state)
                    1: r_max_cnt = HIGH_DO;
                    2: r_max_cnt = 0; // 무음 (박자 구분)
                    3: r_max_cnt = HIGH_DO;
                    4: r_max_cnt = 0;
                    5: r_max_cnt = HIGH_DO;
                    default: r_max_cnt = 0;
                endcase
            end
            3'd4: begin // [문 열림/닫힘] 솔 - 무음 - 솔 (각 100ms)
                case (r_state)
                    1: r_max_cnt = SOL;
                    2: r_max_cnt = 0;   // 100ms 동안 무음 (간격)
                    3: r_max_cnt = SOL;
                    default: r_max_cnt = 0; // 나머지 시간은 무음 처리
                endcase
            end
            default: r_max_cnt = 0;
        endcase
    end

    // 2. 멜로디 연주 로직
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_state <= 0;
            r_time_cnt <= 0;
            r_freq_cnt <= 0;
            buzzer <= 0;
            r_last_sel <= 0;
            r_busy <= 0;
        end else begin
            r_last_sel <= melody_sel;

            // 새로운 명령이 들어오면 시퀀스 리셋 (멜로디 바뀜 체크)
            if (melody_sel != r_last_sel && melody_sel != 0) begin
                r_state <= 1;
                r_time_cnt <= 0;
                r_busy <= 1;
            end

            if (r_busy) begin
                // 시간 카운터 (각 음을 100ms씩 연주)
                if (r_time_cnt >= TIME_100MS - 1) begin
                    r_time_cnt <= 0;
                    // 마지막 음까지 연주하면 종료 (FINISH는 5번, 나머지는 3번)
                    if (r_state >= 6) begin 
                        r_state <= 0;
                        r_busy <= 0;
                    end else begin
                        r_state <= r_state + 1;
                    end
                end else begin
                    r_time_cnt <= r_time_cnt + 1;
                end

                // 실제 소리 발생 (Square Wave)
                if (r_max_cnt == 0) begin
                    buzzer <= 0;
                    r_freq_cnt <= 0;
                end else if (r_freq_cnt >= r_max_cnt - 1) begin
                    r_freq_cnt <= 0;
                    buzzer <= ~buzzer;
                end else begin
                    r_freq_cnt <= r_freq_cnt + 1;
                end
            end else begin
                buzzer <= 0;
            end
        end
    end

endmodule



