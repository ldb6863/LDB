`timescale 1ns / 1ps

module unified_data_sender(
    input clk, reset,
    
    input data_valid,          // 1초(1Hz) tick 신호 (전송 시작 방아쇠)
    input tx_busy,             // UART TX 모듈의 바쁨 상태
    
    // RTC 데이터
    input [47:0] current_time, 
    // DHT11 데이터
    input [7:0] temp, temp_dec,
    input [7:0] humi, humi_dec,
    
    output reg tx_start,
    output reg [7:0] tx_data
);

    reg [5:0] send_cnt; // 최대 43글자이므로 6비트(0~63) 필요
    reg [1:0] state;
    localparam IDLE = 2'd0, SEND = 2'd1, WAIT_HIGH = 2'd2, WAIT_LOW = 2'd3;

    // --- 1. RTC BCD ➔ ASCII 변환 ---
    wire [7:0] yy_10 = current_time[47:44] + 8'h30; wire [7:0] yy_1  = current_time[43:40] + 8'h30;
    wire [7:0] mm_10 = current_time[39:36] + 8'h30; wire [7:0] mm_1  = current_time[35:32] + 8'h30;
    wire [7:0] dd_10 = current_time[31:28] + 8'h30; wire [7:0] dd_1  = current_time[27:24] + 8'h30;
    wire [7:0] hr_10 = current_time[23:20] + 8'h30; wire [7:0] hr_1  = current_time[19:16] + 8'h30;
    wire [7:0] mi_10 = current_time[15:12] + 8'h30; wire [7:0] mi_1  = current_time[11:8]  + 8'h30;
    wire [7:0] ss_10 = current_time[7:4]   + 8'h30; wire [7:0] ss_1  = current_time[3:0]   + 8'h30;

    // --- 2. DHT11 Hex ➔ ASCII 변환 ---
    wire [7:0] t_tens = ((temp % 100) / 10) + 8'h30; wire [7:0] t_ones = (temp % 10) + 8'h30;
    wire [7:0] h_hun  = (humi >= 100) ? 8'h31 : 8'h20;
    wire [7:0] h_tens = ((humi % 100) / 10) + 8'h30; wire [7:0] h_ones = (humi % 10) + 8'h30;

    // --- 3. 전송 상태 머신 ---
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            tx_start <= 0; tx_data <= 0; send_cnt <= 0; state <= IDLE;
        end else begin
            case (state)
                IDLE: begin
                    tx_start <= 0;
                    if (data_valid) begin state <= SEND; send_cnt <= 0; end
                end
                
                SEND: begin
                    if (!tx_busy) begin
                        tx_start <= 1; state <= WAIT_HIGH;
                        
                        // 총 43 Bytes 문자열 조합
                        case (send_cnt)
                            // 시간 파트 (0~18)
                            6'd0:  tx_data <= "2"; 6'd1:  tx_data <= "0"; 6'd2:  tx_data <= yy_10; 6'd3:  tx_data <= yy_1;
                            6'd4:  tx_data <= "-"; 6'd5:  tx_data <= mm_10; 6'd6:  tx_data <= mm_1;
                            6'd7:  tx_data <= "-"; 6'd8:  tx_data <= dd_10; 6'd9:  tx_data <= dd_1;
                            6'd10: tx_data <= " ";
                            6'd11: tx_data <= hr_10; 6'd12: tx_data <= hr_1;
                            6'd13: tx_data <= ":"; 6'd14: tx_data <= mi_10; 6'd15: tx_data <= mi_1;
                            6'd16: tx_data <= ":"; 6'd17: tx_data <= ss_10; 6'd18: tx_data <= ss_1;
                            
                            // 구분자 파트 (19~21)
                            6'd19: tx_data <= " "; 6'd20: tx_data <= "|"; 6'd21: tx_data <= " ";
                            
                            // 온습도 파트 (22~40)
                            6'd22: tx_data <= "T"; 6'd23: tx_data <= ":"; 6'd24: tx_data <= " ";
                            6'd25: tx_data <= t_tens; 6'd26: tx_data <= t_ones; 6'd27: tx_data <= "."; 
                            6'd28: tx_data <= (temp_dec % 10) + 8'h30; 6'd29: tx_data <= "C";
                            6'd30: tx_data <= ","; 6'd31: tx_data <= " ";
                            6'd32: tx_data <= "H"; 6'd33: tx_data <= ":"; 6'd34: tx_data <= " ";
                            6'd35: tx_data <= h_hun;  6'd36: tx_data <= h_tens; 6'd37: tx_data <= h_ones; 
                            6'd38: tx_data <= "."; 6'd39: tx_data <= (humi_dec % 10) + 8'h30; 6'd40: tx_data <= "%";
                            
                            // 줄바꿈 파트 (41~42)
                            6'd41: tx_data <= 8'h0D; // \r
                            6'd42: tx_data <= 8'h0A; // \n
                            default: tx_data <= " ";
                        endcase
                    end
                end
                
                WAIT_HIGH: begin tx_start <= 0; if (tx_busy) state <= WAIT_LOW; end
                WAIT_LOW: begin
                    if (!tx_busy) begin 
                        if (send_cnt == 6'd42) state <= IDLE; // 43글자 전송 완료
                        else begin send_cnt <= send_cnt + 1; state <= SEND; end
                    end
                end
            endcase
        end
    end
endmodule