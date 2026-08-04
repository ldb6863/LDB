`timescale 1ns / 1ps

module rtc_uart_parser(
    input clk, reset,
    input rx_done,
    input [7:0] rx_data,
    output reg set_trigger,
    output reg [47:0] set_time_bcd,
    
    // 새로 추가된 알람 설정 포트
    output reg set_alarm_trig,
    output reg [15:0] alarm_time_bcd
);
    reg [3:0] r_state;
    reg [47:0] r_temp_bcd;
    reg [15:0] r_alarm_temp;
    reg [3:0] r_num_cnt;
    
    localparam S_IDLE=0, S_S=1, S_E=2, S_T=3;
    localparam S_R=4, S_T2=5, S_C=6, S_NUMS=7; // setrtc 경로
    localparam S_A=8, S_L=9, S_A2=10, S_R2=11, S_M=12, S_ALARM_NUMS=13; // setalarm 경로

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_state <= S_IDLE;
            set_trigger <= 0; set_time_bcd <= 0; 
            set_alarm_trig <= 0; alarm_time_bcd <= 0; r_num_cnt <= 0;
        end else begin
            set_trigger <= 0; set_alarm_trig <= 0; // 펄스 초기화
            if (rx_done) begin
                case (r_state)
                    S_IDLE: if (rx_data == "s") r_state <= S_S;
                    S_S:    if (rx_data == "e") r_state <= S_E; else r_state <= S_IDLE;
                    S_E:    if (rx_data == "t") r_state <= S_T; else r_state <= S_IDLE;
                    S_T:    begin
                                if (rx_data == "r") r_state <= S_R;      // setrtc...
                                else if (rx_data == "a") r_state <= S_A; // setalarm...
                                else r_state <= S_IDLE;
                            end
                            
                    // --- setrtc 경로 ---
                    S_R:    if (rx_data == "t") r_state <= S_T2; else r_state <= S_IDLE;
                    S_T2:   if (rx_data == "c") begin r_state <= S_NUMS; r_num_cnt <= 0; end else r_state <= S_IDLE;
                    S_NUMS: begin
                        if (rx_data >= 8'h30 && rx_data <= 8'h39) begin
                            r_temp_bcd <= {r_temp_bcd[43:0], rx_data[3:0]};
                            if (r_num_cnt == 11) begin 
                                set_time_bcd <= {r_temp_bcd[43:0], rx_data[3:0]};
                                set_trigger <= 1; r_state <= S_IDLE; 
                            end else r_num_cnt <= r_num_cnt + 1;
                        end else r_state <= S_IDLE;
                    end
                    
                    // --- setalarm 경로 ---
                    S_A:    if (rx_data == "l") r_state <= S_L; else r_state <= S_IDLE;
                    S_L:    if (rx_data == "a") r_state <= S_A2; else r_state <= S_IDLE;
                    S_A2:   if (rx_data == "r") r_state <= S_R2; else r_state <= S_IDLE;
                    S_R2:   if (rx_data == "m") begin r_state <= S_ALARM_NUMS; r_num_cnt <= 0; end else r_state <= S_IDLE;
                    S_ALARM_NUMS: begin
                        if (rx_data >= 8'h30 && rx_data <= 8'h39) begin
                            r_alarm_temp <= {r_alarm_temp[11:0], rx_data[3:0]};
                            if (r_num_cnt == 3) begin // 4자리 숫자(HHMM)
                                alarm_time_bcd <= {r_alarm_temp[11:0], rx_data[3:0]};
                                set_alarm_trig <= 1; r_state <= S_IDLE; 
                            end else r_num_cnt <= r_num_cnt + 1;
                        end else r_state <= S_IDLE;
                    end
                    
                    default: r_state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
