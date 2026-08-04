`timescale 1ns / 1ps

module master_fsm(
    input clk, reset,
    
    // --- 1. 설정 및 조작 입력 ---
    input [1:0] mode_sel,       // 가동 시간 선택 (1분, 2분, 30분)
    input set_time_trig,        // UART/Rotary 시간 설정 신호 (설정 중 중단용)
    
    // --- 2. 하위 모듈 센서 입력 ---
    input alarm_match,          // DS1302: 예약 시간 일치
    input [11:0] dist_cm,       // 초음파: 거리 데이터

    // --- 3. 시스템 출력 제어 ---
    output reg system_on            // 서보 모터 및 에어컨 가동 허가 신호
);

    // 시스템 상태 정의 (경보 상태 제거)
    localparam S_IDLE       = 3'd0;
    localparam S_ALARM_RUN  = 3'd1;
    localparam S_DETECT_RUN = 3'd2;
    localparam S_SETTING    = 3'd4;

    reg [2:0] state;

    // 타이머 파라미터 및 레지스터
    localparam CNT_1MIN  = 9'd500;    
    localparam CNT_29MIN = 10'd1000;  
    // localparam CNT_1MIN  = 33'd6_000_000_000;    
    // localparam CNT_29MIN = 38'd174_000_000_000;  
    reg [37:0] r_timer_cnt;

    // 상태 전이 감지용 (알람 엣지 검출)
    reg r_alarm_match_d;

    // ========================================================
    // 1. 상태 전이 (State Transition) 로직
    // ========================================================
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S_IDLE;
            r_timer_cnt <= 0;
            r_alarm_match_d <= 0;
        end else begin
            r_alarm_match_d <= alarm_match;

            // 최고 우선순위: 시간 설정 중일 때 강제 정지
            if (set_time_trig) begin
                state <= S_SETTING;
                r_timer_cnt <= 0;
            end 
            else begin
                case (state)
                    S_IDLE: begin
                        r_timer_cnt <= 0;
                        // 알람 시작 시 또는 사람 감지 시 가동
                        if (alarm_match && !r_alarm_match_d) state <= S_ALARM_RUN;
                        else if (dist_cm > 0 && dist_cm <= 20) state <= S_DETECT_RUN;
                    end

                    S_ALARM_RUN: begin
                        r_timer_cnt <= r_timer_cnt + 1; // 가동 시간 카운트
                        case (mode_sel)
                            2'b01: if (r_timer_cnt >= CNT_1MIN) state <= S_IDLE; // 총 2분
                            2'b10: if (r_timer_cnt >= CNT_29MIN) state <= S_IDLE; // 총 30분
                            default: if (!alarm_match) state <= S_IDLE; // 기본 1분
                        endcase
                    end

                    S_DETECT_RUN: begin
                        // 사람이 감지 범위를 벗어나면 정지
                        if (dist_cm > 20 || dist_cm == 0) state <= S_IDLE;
                    end

                    S_SETTING: begin
                        // 설정이 완료되면 대기 상태로 복귀
                        if (!set_time_trig) state <= S_IDLE;
                    end

                    default: state <= S_IDLE;
                endcase
            end
        end
    end

    // ========================================================
    // 2. 상태에 따른 출력 (Output Logic) 
    // ========================================================
    always @(*) begin
        system_on = 1'b0;

        case (state)
            S_ALARM_RUN:  system_on = 1'b1; // 알람 가동
            S_DETECT_RUN: system_on = 1'b1; // 사람 감지 가동
            default:      system_on = 1'b0;
        endcase
    end

endmodule
