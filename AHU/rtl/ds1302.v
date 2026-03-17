// `timescale 1ns / 1ps

// module ds1302 #(
//     parameter HALF_PERIOD = 25
// )(
//     input clk,
//     input reset,
//     input ds1302_start_trigger,
//     input [7:0] cmd_byte,
//     input [7:0] write_data,
    
//     inout ds_io,
//     output reg ds_ce,
//     output ds_sclk,        
//     output reg [7:0] read_data,
//     output reg valid
// );
//     // ========================================================
//     // 1. 내부 SCLK 발전기
//     // ========================================================
//     reg [7:0] r_clk_cnt; 
//     reg r_sclk;
//     assign ds_sclk = r_sclk; 
    
//     localparam IDLE    = 3'd0;
//     localparam ACTIVE  = 3'd1;
//     localparam CE_HOLD = 3'd2; 
//     localparam DONE    = 3'd3;
//     reg [2:0] r_state;

//     always @(posedge clk or posedge reset) begin
//         if (reset) begin
//             r_sclk <= 0; r_clk_cnt <= 0;
//         end else if (r_state == ACTIVE) begin
//             if (r_clk_cnt >= HALF_PERIOD - 1) begin
//                 r_sclk <= ~r_sclk; r_clk_cnt <= 0;
//             end else r_clk_cnt <= r_clk_cnt + 1;
//         end else if (r_state == CE_HOLD) begin 
//             r_sclk <= 0;
//             if (r_clk_cnt >= HALF_PERIOD - 1) r_clk_cnt <= 0;
//             else r_clk_cnt <= r_clk_cnt + 1;
//         end else begin
//             r_sclk <= 0; r_clk_cnt <= 0;
//         end
//     end

//     // ========================================================
//     // 2. 엣지 검출 (1클럭 지연 없는 완벽 동기화 버전)
//     // ========================================================
//     // 카운터가 꽉 차서 SCLK가 뒤집어지기 직전의 타이밍을 예측
//     wire w_pos_edge = (r_state == ACTIVE) && (r_clk_cnt == HALF_PERIOD - 1) && (r_sclk == 1'b0);
//     wire w_neg_edge = (r_state == ACTIVE) && (r_clk_cnt == HALF_PERIOD - 1) && (r_sclk == 1'b1);

//     // ========================================================
//     // 3. 내부 변수 
//     // ========================================================
//     reg [4:0] r_bit_idx;
//     reg r_is_read_mode;
//     reg [7:0] r_shift_cmd;
//     reg [7:0] r_shift_tx;
//     reg [7:0] r_shift_rx;
    
//     reg r_io_mode;           
//     reg r_o_data;
//     assign ds_io = r_io_mode ? 1'bz : r_o_data;

//     // ========================================================
//     // 4. 메인 제어 로직 (첫 비트 강제 지연)
//     // ========================================================
//     always @(posedge clk or posedge reset) begin
//         if (reset) begin
//             r_state <= IDLE; ds_ce <= 0; r_io_mode <= 1; valid <= 0;
//             read_data <= 0; r_bit_idx <= 0; 
//             r_o_data <= 1'b1; // 초기값을 1로 고정
//         end else begin
//             case (r_state)
//                 IDLE: begin
//                     valid <= 0;
//                     if (ds1302_start_trigger) begin
//                         r_state <= ACTIVE;
//                         ds_ce <= 1;
//                         r_bit_idx <= 0;
//                         r_is_read_mode <= cmd_byte[0];
                        
//                         r_io_mode <= 0; 
//                         // ★ CE가 뜰 때 IO가 미리 떨어지지 않게 1(High) 상태 유지
//                         r_o_data <= 1'b1; 
//                         // ★ 첫 비트를 빼지 않고 원본 데이터를 그대로 장전
//                         r_shift_cmd <= cmd_byte; 
//                         r_shift_tx <= write_data;
//                     end
//                 end

//                 ACTIVE: begin
//                     // [SCLK 상승 엣지 (0 -> 1)]
//                     if (w_pos_edge) begin
//                         // ★ 모든 데이터(명령어 8비트 + 데이터 8비트)를 SCLK가 상승하는 
//                         // "정확히 그 순간"에 맞춰서 일제히 출력합니다!
                        
//                         // 1. 명령어 전송 (0~7 비트)
//                         if (r_bit_idx < 8) begin 
//                             r_o_data <= r_shift_cmd[0];
//                             r_shift_cmd <= r_shift_cmd >> 1;
//                         end 
//                         // 2. 방향 전환 및 데이터 전송 시작 (8 비트)
//                         else if (r_bit_idx == 8) begin 
//                             if (!r_is_read_mode) begin
//                                 r_o_data <= r_shift_tx[0];
//                                 r_shift_tx <= r_shift_tx >> 1;
//                             end else begin
//                                 r_io_mode <= 1; // 읽기 모드면 이때 제어권 넘김
//                             end
//                         end 
//                         // 3. 남은 데이터 전송 (9~15 비트)
//                         else if (r_bit_idx > 8 && r_bit_idx < 16) begin 
//                             if (!r_is_read_mode) begin
//                                 r_o_data <= r_shift_tx[0];
//                                 r_shift_tx <= r_shift_tx >> 1;
//                             end
//                         end
                        
//                         // [읽기 모드 수신] 
//                         if (r_is_read_mode && r_bit_idx >= 8 && r_bit_idx < 16) begin
//                             r_shift_rx <= {ds_io, r_shift_rx[7:1]}; 
//                         end
                        
//                         r_bit_idx <= r_bit_idx + 1; 
//                     end
                    
//                     // [SCLK 하강 엣지 (1 -> 0)]
//                     if (w_neg_edge) begin
//                         // ★ 데이터 전송 로직을 전부 위(상승 엣지)로 치워버렸으므로, 
//                         // 여기서는 그냥 통신이 16비트 다 돌았는지만 체크하고 끝냅니다.
//                         if (r_bit_idx == 16) begin
//                             r_state <= CE_HOLD;
//                         end
//                     end 
//                 end

//                 CE_HOLD: begin
//                     if (r_clk_cnt >= HALF_PERIOD - 1) begin
//                         r_state <= DONE;
//                     end
//                 end

//                 DONE: begin
//                     ds_ce <= 0;
//                     r_io_mode <= 1;
//                     if (r_is_read_mode) read_data <= r_shift_rx;
//                     valid <= 1;
//                     r_state <= IDLE;
//                 end

//                 default: r_state <= IDLE;
//             endcase
//         end
//     end
// endmodule

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