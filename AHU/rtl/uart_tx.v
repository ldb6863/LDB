`timescale 1ns / 1ps

module uart_tx #(
    parameter BPS = 9600
) (
    input clk,
    input reset,
    input [7:0] tx_data,
    input tx_start,
    output reg tx,
    output reg tx_done,
    output reg tx_busy
);

    localparam S_IDLE = 2'b00;
    localparam S_START_BIT = 2'b01;
    localparam S_DATA_8BITS = 2'b10;
    localparam S_STOP_BIT = 2'b11;
    localparam DIVIDER_CNT = 100_000_000 / BPS;  

    reg [1:0] r_state;   // state teansition 
    reg [3:0] r_bit_cnt;   // 전송 bit cnt
    reg [7:0] r_data_reg;  // 전송할 1 byte 
    reg [15:0] r_baud_cnt;   // 10416ns
    reg r_baud_tick;      // 10416ns 마다 1 tick발생용

    // 10416ns 마다 1 tick 발생 --> r_baud_tick

    always @(posedge clk, posedge reset) begin
        if (reset) begin
            r_baud_cnt <= 0;
            r_baud_tick <= 0;
        end else begin
            if (r_baud_cnt >= DIVIDER_CNT-1) begin
                r_baud_cnt <=0;
                r_baud_tick <= 1;
            end else begin
                r_baud_cnt <= r_baud_cnt + 1;
                r_baud_tick <=0;
            end 
        end 
    end 

      always @(posedge clk, posedge reset) begin
        if (reset) begin
            r_state <= S_IDLE;
            r_bit_cnt <= 0;
            r_data_reg <=0;
            tx_done <=0;
            tx_busy <=0;
            tx <= 1;   // IDLE: HIGH
        end else begin
            case (r_state)
            S_IDLE: begin
                tx_done <= 0;
                if (tx_start) begin
                    r_state <= S_START_BIT;
                    r_data_reg <= tx_data;
                    tx_busy <= 1'b1;  
                    r_bit_cnt <= 0;
                end 
            end 

            S_START_BIT: begin
                if (r_baud_tick) begin
                    tx <= 1'b0;   // start bit
                    r_state <= S_DATA_8BITS;
                end 
            end

            S_DATA_8BITS: begin
                if (r_baud_tick) begin
                    tx <= r_data_reg[r_bit_cnt];  
                    if (r_bit_cnt == 4'd7)  begin
                        r_state <= S_STOP_BIT;
                    end else begin
                        r_bit_cnt <= r_bit_cnt + 1; 
                    end 
                end 
            end 

            S_STOP_BIT: begin
                if (r_baud_tick) begin
                    tx <= 1'b1;  // STOP bit 
                    tx_done <= 1;   // 1 byte 전송 완료 
                    tx_busy <=0; 
                    r_state <= S_IDLE;
                end 
            end 

            default: r_state <= S_IDLE;
            endcase
        end 
    end   
endmodule
