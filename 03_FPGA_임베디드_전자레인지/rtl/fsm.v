`timescale 1ns / 1ps

module fsm (
    input clk, reset, tick_1ms,
    input btn_start, btn_stop, btn_door,
    input btn_10s, btn_30s, btn_1m,
    input is_time_over,       // Timer -> FSM: 종료 보고
    input [15:0] seg_data,    
    
    output reg timer_en, timer_clr,
    output reg [2:0] timer_add,
    output reg motor_en, door_pos,
    output reg [2:0] melody_sel,
    output reg [1:0] out_state // FND 제어용 현재 상태 출력
);

    // 상태 정의
    localparam IDLE=2'b00, COOK=2'b01, PAUSE=2'b10, FINISH=2'b11;
    reg [1:0] curr_state, next_state;
    reg [11:0] r_finish_cnt;

    // --- 1. Edge Detectors (버튼의 상승 엣지 검출) ---
    reg [5:0] r_btn_old;
    wire [5:0] w_btn_pedge;
    always @(posedge clk) r_btn_old <= {btn_door, btn_stop, btn_start, btn_1m, btn_30s, btn_10s};
    assign w_btn_pedge = {btn_door, btn_stop, btn_start, btn_1m, btn_30s, btn_10s} & ~r_btn_old;

    // --- 2. Door State (문 열림 상태 유지) ---
    reg r_door_open;
    always @(posedge clk or posedge reset) begin
        if (reset) r_door_open <= 1'b0;
        else if (w_btn_pedge[5]) r_door_open <= ~r_door_open;
    end

    // --- 3. State Register ---
    always @(posedge clk or posedge reset) begin
        if (reset) curr_state <= IDLE;
        else curr_state <= next_state;
    end

    // --- 4. Next State Logic (상태 전이 조건 수정) ---
    always @(*) begin
        next_state = curr_state;
        case (curr_state)
            IDLE:   if (w_btn_pedge[3] && seg_data != 16'h0000 && !r_door_open) next_state = COOK;
            
            COOK:   if (w_btn_pedge[4]) next_state = IDLE;       // STOP 누르면 즉시 IDLE
                    else if (r_door_open || w_btn_pedge[3]) next_state = PAUSE; // 문 열거나 START 누르면 PAUSE
                    else if (is_time_over) next_state = FINISH;  // 시간 다 되면 FINISH
            
            PAUSE:  if (w_btn_pedge[4]) next_state = IDLE;       // STOP 누르면 즉시 IDLE
                    else if (!r_door_open && w_btn_pedge[3]) next_state = COOK; // 문 닫고 START 누르면 재개
            
            FINISH: if (w_btn_pedge[4] || r_finish_cnt >= 3000) next_state = IDLE; // 3초 경과 혹은 STOP 시 IDLE
            
            default: next_state = IDLE;
        endcase
    end

    // --- 5. Counters (FINISH 시간 및 도어 알림용) ---
    reg [9:0]  r_door_snd_cnt;
    always @(posedge clk or posedge reset) begin
        if (reset) begin 
            r_finish_cnt <= 0; 
            r_door_snd_cnt <= 0; 
        end else begin
            // FINISH 상태에서 1ms씩 카운트 (3초 체크용)
            if (curr_state == FINISH) begin
                if (tick_1ms) r_finish_cnt <= r_finish_cnt + 1;
            end else begin
                r_finish_cnt <= 0;
            end
            
            // 문 열림 알림음 카운터
            if (w_btn_pedge[5]) r_door_snd_cnt <= 600;
            else if (r_door_snd_cnt > 0 && tick_1ms) r_door_snd_cnt <= r_door_snd_cnt - 1;
        end
    end

    // --- 6. Output Assignment (제어 신호 수정 핵심) ---
    always @(*) begin
        // 상태 출력
        out_state = curr_state;
        door_pos  = r_door_open;
        
        // 타이머 및 모터 활성화
        timer_en  = (curr_state == COOK);
        motor_en  = (curr_state == COOK);

        // [수정 1] 시간 추가: COOK(동작 중) 상태에서도 버튼이 먹도록 FINISH만 아니면 허용
        timer_add = (curr_state != FINISH) ? w_btn_pedge[2:0] : 3'b000;

        // [수정 2] 타이머 초기화: 어떤 상태에서든 STOP(취소) 버튼을 누르면 즉시 0000으로 클리어
        timer_clr = w_btn_pedge[4];

        // 멜로디 선택
        case (curr_state)
            COOK:   melody_sel = 3'd1;
            PAUSE:  melody_sel = 3'd2;
            FINISH: melody_sel = 3'd3;
            default: melody_sel = (r_door_snd_cnt > 0) ? 3'd4 : 3'd0;
        endcase
    end
endmodule