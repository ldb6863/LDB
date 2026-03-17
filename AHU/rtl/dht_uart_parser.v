`timescale 1ns / 1ps

module dht_uart_parser(
    input clk,
    input reset,
    input [7:0] rx_data,     // uart_rx에서 수신된 1바이트
    input rx_done,           // 수신 완료 펄스
    output reg [7:0] target_temp,
    output reg [7:0] target_temp_dec
);

    // "tempXX.Y" 형식 파싱을 위한 상태 머신
    localparam S_IDLE = 0, S_T = 1, S_E = 2, S_M = 3, S_P = 4;
    localparam S_VAL_10 = 5, S_VAL_1 = 6, S_DOT = 7, S_VAL_DEC = 8;
    
    reg [3:0] state;
    reg [7:0] temp_10, temp_1;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S_IDLE;
            target_temp <= 8'd24;     // 기본 설정 온도 24.0도
            target_temp_dec <= 8'd0;
        end else if (rx_done) begin
            case (state)
                S_IDLE: if (rx_data == "t") state <= S_T; else state <= S_IDLE;
                S_T:    if (rx_data == "e") state <= S_E; else state <= S_IDLE;
                S_E:    if (rx_data == "m") state <= S_M; else state <= S_IDLE;
                S_M:    if (rx_data == "p") state <= S_P; else state <= S_IDLE;
                S_P: begin // 10의 자리 숫자 수신
                    if (rx_data >= "0" && rx_data <= "9") begin
                        temp_10 <= rx_data - 8'h30;
                        state <= S_VAL_10;
                    end else state <= S_IDLE;
                end
                S_VAL_10: begin // 1의 자리 숫자 수신
                    if (rx_data >= "0" && rx_data <= "9") begin
                        temp_1 <= rx_data - 8'h30;
                        state <= S_VAL_1;
                    end else state <= S_IDLE;
                end
                S_VAL_1: if (rx_data == ".") state <= S_DOT; else state <= S_IDLE;
                S_DOT: begin // 소수점 첫째 자리 수신 및 최종 업데이트
                    if (rx_data >= "0" && rx_data <= "9") begin
                        target_temp <= (temp_10 * 10) + temp_1;
                        target_temp_dec <= rx_data - 8'h30;
                        state <= S_IDLE; // 파싱 완료, IDLE로 복귀
                    end else state <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule