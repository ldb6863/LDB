`timescale 1ns / 1ps

module dht11(
    input clk,
    input reset,
    input start_trigger,   
    inout dht11_pin,
    output reg [7:0] temp,
    output reg [7:0] temp_dec,
    output reg [7:0] humi,
    output reg [7:0] humi_dec,
    output reg data_valid
);

    // 1. 입력 신호 동기화 (Metastability 방지)
    reg dht_in_1, dht_in_2;
    always @(posedge clk) begin
        dht_in_1 <= dht11_pin;
        dht_in_2 <= dht_in_1;
    end
    wire dht_in = dht_in_2;

    // 2. inout 핀 제어
    reg dht_out, dht_dir;
    assign dht11_pin = dht_dir ? dht_out : 1'bz;

    // 3. 상태 머신
    localparam S_IDLE       = 4'd0;
    localparam S_START_LOW  = 4'd1;
    localparam S_START_HIGH = 4'd2;
    localparam S_ACK_LOW    = 4'd3;
    localparam S_ACK_HIGH   = 4'd4;
    localparam S_READ_LOW   = 4'd5;
    localparam S_READ_HIGH  = 4'd6;
    localparam S_LAST_LOW   = 4'd7;
    localparam S_DONE       = 4'd8;

    reg [3:0] state;
    reg [31:0] timer;
    reg [5:0] bit_cnt;
    reg [39:0] dht_data;

    always @(posedge clk) begin
        if(reset) begin
            state <= S_IDLE;
            timer <= 0;
            dht_dir <= 0;
            dht_out <= 0;
            bit_cnt <= 0;
            data_valid <= 0;
            temp <= 0;
            humi <= 0;
        end else begin
            // data_valid는 1클럭만 튕기도록 유지
            if(data_valid) data_valid <= 0; 
            
            case(state)
                S_IDLE: begin
                    dht_dir <= 0; 
                    if(start_trigger) begin
                        state <= S_START_LOW;
                        timer <= 0;
                    end
                end
                
                S_START_LOW: begin
                    dht_dir <= 1; 
                    dht_out <= 0; 
                    // 데이터시트: 최소 18ms 동안 Low 유지 (1,800,000 클럭)
                    if(timer >= 1_800_000) begin 
                        state <= S_START_HIGH;
                        timer <= 0;
                        dht_dir <= 0; // High-Z 상태로 전환하여 센서 응답 대기
                    end else timer <= timer + 1;
                end
                
                S_START_HIGH: begin
                    // 데이터시트: MCU가 선을 놓고 20~40us 대기
                    if(!dht_in) begin
                        state <= S_ACK_LOW;
                        timer <= 0;
                    end else if(timer > 100_000) begin // 1ms Timeout
                        state <= S_IDLE;
                    end else timer <= timer + 1;
                end
                
                S_ACK_LOW: begin
                    // 데이터시트: 센서가 80us 동안 Low 유지
                    if(dht_in) begin
                        state <= S_ACK_HIGH;
                        timer <= 0;
                    end else if(timer > 100_000) state <= S_IDLE; 
                    else timer <= timer + 1;
                end
                
                S_ACK_HIGH: begin
                    // 데이터시트: 센서가 80us 동안 High 유지 후 데이터 전송 시작
                    if(!dht_in) begin
                        state <= S_READ_LOW;
                        timer <= 0;
                        bit_cnt <= 0;
                    end else if(timer > 100_000) state <= S_IDLE; 
                    else timer <= timer + 1;
                end
                
                S_READ_LOW: begin
                    // 데이터시트: 각 비트의 시작은 항상 50us의 Low 신호
                    if(dht_in) begin
                        state <= S_READ_HIGH;
                        timer <= 0;
                    end else if(timer > 100_000) state <= S_IDLE;
                    else timer <= timer + 1;
                end
                
                S_READ_HIGH: begin
                    // 데이터시트: '0'은 26~28us, '1'은 70us High 유지
                    if(!dht_in) begin
                        // 중간값인 40us(4000)를 기준으로 판별
                        dht_data <= {dht_data[38:0], (timer > 4000) ? 1'b1 : 1'b0};
                        bit_cnt <= bit_cnt + 1;
                        timer <= 0;
                        
                        if(bit_cnt == 39) state <= S_LAST_LOW; // 40비트 완료시 종료 구간으로
                        else state <= S_READ_LOW; // 다음 비트로
                    end else if(timer > 100_000) state <= S_IDLE; 
                    else timer <= timer + 1;
                end
                
                S_LAST_LOW: begin
                    // 데이터시트: 마지막 데이터 전송 후 센서가 50us 동안 Low를 유지
                    if(dht_in) begin // 센서가 버스를 High로 놓아줄 때까지 대기
                        state <= S_DONE;
                    end else if(timer > 100_000) state <= S_IDLE;
                    else timer <= timer + 1;
                end

                S_DONE: begin
                    // 데이터시트 Checksum 방식: 상위 4바이트 합계의 하위 8비트가 마지막 바이트와 일치해야 함
                    if(dht_data[39:32] + dht_data[31:24] + dht_data[23:16] + dht_data[15:8] == dht_data[7:0]) begin
                        humi <= dht_data[39:32]; // 8bit integral RH data
                        humi_dec <= dht_data[31:24];
                        temp <= dht_data[23:16]; // 8bit integral T data
                        temp_dec <= dht_data[15:8];
                        data_valid <= 1; 
                    end
                    state <= S_IDLE;
                end
                
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
