`timescale 1ns / 1ps

module ds1302 #(
    parameter HALF_PERIOD = 25
)(
    input clk,
    input reset,
    input ds1302_start_trigger,
    input [7:0] cmd_byte,
    input [7:0] write_data,
    
    inout ds_io,
    output reg ds_ce,
    output ds_sclk,        
    output reg [7:0] read_data,
    output reg valid
);
    // 1. 내부 SCLK 발전기
    reg [7:0] r_clk_cnt; // 오버플로우 방지 (16비트)
    reg r_sclk;
    assign ds_sclk = r_sclk; 
    
    // FSM
    localparam IDLE    = 3'd0;
    localparam ACTIVE  = 3'd1;
    localparam CE_HOLD = 3'd2; // tCCH 확보를 위한 대기 상태
    localparam DONE    = 3'd3;
    reg [2:0] r_state;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_sclk <= 0; r_clk_cnt <= 0;
        end else if (r_state == ACTIVE) begin
            if (r_clk_cnt >= HALF_PERIOD - 1) begin
                r_sclk <= ~r_sclk; r_clk_cnt <= 0;
            end else r_clk_cnt <= r_clk_cnt + 1;
        end else if (r_state == CE_HOLD) begin 
            // HOLD 상태에서는 클럭은 0으로 고정하고 시간만 끎 (5us 대기)
            r_sclk <= 0;
            if (r_clk_cnt >= HALF_PERIOD - 1) r_clk_cnt <= 0;
            else r_clk_cnt <= r_clk_cnt + 1;
        end else begin
            r_sclk <= 0; r_clk_cnt <= 0;
        end
    end

    // 2. 엣지 검출
    reg r_sclk_d;
    always @(posedge clk or posedge reset) begin
        if (reset) r_sclk_d <= 0;
        else r_sclk_d <= r_sclk; 
    end

    wire w_pos_edge = (r_sclk == 1'b1 && r_sclk_d == 1'b0);
    wire w_neg_edge = (r_sclk == 1'b0 && r_sclk_d == 1'b1);

    // 3. 내부 변수
    reg [4:0] r_bit_idx;
    reg r_is_read_mode;
    reg [7:0] r_shift_cmd;
    reg [7:0] r_shift_tx;
    reg [7:0] r_shift_rx;
    
    reg r_io_mode;           
    reg r_o_data;
    assign ds_io = r_io_mode ? 1'bz : r_o_data;

    // 4. 메인 제어 로직
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_state <= IDLE; ds_ce <= 0; r_io_mode <= 1; valid <= 0;
            read_data <= 0; r_bit_idx <= 0; r_o_data <= 0;
        end else begin
            case (r_state)
                IDLE: begin
                    valid <= 0;
                    if (ds1302_start_trigger) begin
                        r_state <= ACTIVE;
                        ds_ce <= 1;
                        r_bit_idx <= 0;
                        r_is_read_mode <= cmd_byte[0];
                        
                        r_io_mode <= 0; 
                        r_o_data <= cmd_byte[0]; 
                        r_shift_cmd <= {1'b0, cmd_byte[7:1]};
                        r_shift_tx <= write_data;
                    end
                end

                ACTIVE: begin
                    if (w_neg_edge) begin
                        if (r_bit_idx < 8) begin 
                            r_o_data <= r_shift_cmd[0];
                            r_shift_cmd <= r_shift_cmd >> 1;
                        end else if (r_bit_idx == 8) begin 
                            if (!r_is_read_mode) begin
                                r_o_data <= r_shift_tx[0];
                                r_shift_tx <= r_shift_tx >> 1;
                            end else begin
                                r_io_mode <= 1; 
                            end
                        end else if (r_bit_idx > 8 && r_bit_idx < 16) begin 
                            if (!r_is_read_mode) begin
                                r_o_data <= r_shift_tx[0];
                                r_shift_tx <= r_shift_tx >> 1;
                            end
                        end
                        
                        // 16번째 클럭이 내려간 뒤, 바로 끄지 않고 HOLD 상태로 넘어감
                        if (r_bit_idx == 16) begin
                            r_state <= CE_HOLD;
                        end
                    end 
                    
                    if (w_pos_edge) begin
                        if (r_is_read_mode && r_bit_idx >= 8 && r_bit_idx < 16) begin
                            r_shift_rx <= {ds_io, r_shift_rx[7:1]}; 
                        end
                        r_bit_idx <= r_bit_idx + 1; 
                    end
                end

                CE_HOLD: begin
                    // tCCH 규약 만족을 위해 5us(HALF_PERIOD) 동안 칩이 소화할 시간을 준 뒤 종료
                    if (r_clk_cnt >= HALF_PERIOD - 1) begin
                        r_state <= DONE;
                    end
                end

                DONE: begin
                    ds_ce <= 0;
                    r_io_mode <= 1;
                    if (r_is_read_mode) read_data <= r_shift_rx;
                    valid <= 1;
                    r_state <= IDLE;
                end

                default: r_state <= IDLE;
            endcase
        end
    end
endmodule
