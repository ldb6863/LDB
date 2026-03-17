`timescale 1ns / 1ps

module dht11_fsm(
    input clk, reset,
    
    // 1. 센서 드라이버(dht11_controller)로부터 수집
    input dht_valid,
    input [7:0] dht_temp, dht_temp_dec,
    input [7:0] dht_humi, dht_humi_dec,
    
    // 2. 통신 모듈(uart_tx)의 상태 확인
    input tx_busy,
    
    // 3. FND와 UART Sender로 하달할 명령 및 정리된 데이터
    output reg [7:0] display_temp, display_humi,         // FND로 갈 안정적인 데이터
    output reg [7:0] send_temp, send_temp_dec,           // UART로 갈 데이터
    output reg [7:0] send_humi, send_humi_dec,
    output reg uart_start_trigger                        // UART 전송 시작 명령
);

    // 상태 정의 (State Machine)
    localparam S_IDLE      = 2'd0; // 평소: 센서 데이터 기다림
    localparam S_LATCH     = 2'd1; // 데이터 수신: 안전하게 복사 및 저장
    localparam S_UART_SEND = 2'd2; // 전송 명령: UART Sender에게 전송 지시
    localparam S_WAIT_UART = 2'd3; // 대기: UART 전송 끝날 때까지 대기

    reg [1:0] state;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S_IDLE;
            uart_start_trigger <= 0;
            display_temp <= 0; display_humi <= 0;
            send_temp <= 0; send_temp_dec <= 0;
            send_humi <= 0; send_humi_dec <= 0;
        end else begin
            uart_start_trigger <= 0; // 펄스 초기화
            
            case (state)
                S_IDLE: begin
                    // 센서에서 1~2초마다 한 번씩 valid 펄스가 올라오면 작동 시작!
                    if (dht_valid) begin
                        state <= S_LATCH;
                    end
                end
                
                S_LATCH: begin
                    // 데이터를 FSM 내부 안전 금고에 보관 (화면 깜빡임이나 데이터 깨짐 방지)
                    display_temp <= dht_temp;
                    display_humi <= dht_humi >> 1;
                    
                    send_temp <= dht_temp; 
                    send_temp_dec <= dht_temp_dec;
                    send_humi <= dht_humi >> 1; 
                    send_humi_dec <= dht_humi_dec >> 1;
                    
                    
                    state <= S_UART_SEND;
                end
                
                S_UART_SEND: begin
                    // UART가 쉬고 있는지 확인 후 전송 명령 하달!
                    if (!tx_busy) begin
                        uart_start_trigger <= 1; 
                        state <= S_WAIT_UART;
                    end
                end
                
                S_WAIT_UART: begin
                    // UART 전송이 완전히 끝날 때까지 대기 후 다시 평화로운 IDLE 상태로 복귀
                    if (!tx_busy) begin
                        state <= S_IDLE;
                    end
                end
            endcase
        end
    end
endmodule