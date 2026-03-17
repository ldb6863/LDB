`timescale 1ns / 1ps

module fnd_control(
    input clk,
    input reset,
    input tick_1ms,         // 자릿수 전환용 (1kHz)
    input tick_1s,          // DP 깜빡임용
    input tick_500ms,       // 종료 시 숫자 깜빡임용
    input [1:0] curr_state, // FSM에서 오는 현재 상태
    input [15:0] seg_data,  // {m10, m1, s10, s1}
    output reg [3:0] an,    
    output reg [7:0] seg    
);

    localparam IDLE=2'b00, COOK=2'b01, PAUSE=2'b10, FINISH=2'b11;

    reg [1:0] sel;
    reg [3:0] hex_value;
    reg dp_state;
    reg blink_state; 

    // 1. 자릿수 선택 카운터 (Multiplexing)
    always @(posedge clk or posedge reset) begin
        if (reset) sel <= 2'b00;
        else if (tick_1ms) sel <= sel + 1;
    end

    // 2. 깜빡임 로직
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            dp_state <= 1'b1;
            blink_state <= 1'b0;
        end else begin
            // 조리 중일 때만 소수점(DP) 깜빡임
            if (curr_state == COOK) begin
                if (tick_1s) dp_state <= ~dp_state;
            end else begin
                dp_state <= 1'b0; // 평소에는 소수점 켜두기 (0이 On인 경우 기준)
            end

            // FINISH 상태에서만 사용할 0.5초 깜빡임 신호
            if (tick_500ms) blink_state <= ~blink_state;
        end
    end

    // 3. 데이터 할당 및 FINISH 깜빡임 제어
    always @(*) begin
        // FINISH 상태이고 깜빡임 신호가 1일 때만 전체 소등
        if (curr_state == FINISH && blink_state) begin
            an = 4'b1111; // 모든 자릿수 끄기
            hex_value = 4'h0;
        end else begin
            case (sel)
                2'b00: begin an = 4'b1110; hex_value = seg_data[3:0];   end
                2'b01: begin an = 4'b1101; hex_value = seg_data[7:4];   end
                2'b10: begin an = 4'b1011; hex_value = seg_data[11:8];  end
                2'b11: begin an = 4'b0111; hex_value = seg_data[15:12]; end
                default: begin an = 4'b1111; hex_value = 4'h0; end
            endcase
        end
    end

    // 4. 7-Segment Decoder
    always @(*) begin
        case (hex_value)
            4'h0: seg[6:0] = 7'b1000000; 4'h1: seg[6:0] = 7'b1111001;
            4'h2: seg[6:0] = 7'b0100100; 4'h3: seg[6:0] = 7'b0110000;
            4'h4: seg[6:0] = 7'b0011001; 4'h5: seg[6:0] = 7'b0010010;
            4'h6: seg[6:0] = 7'b0000010; 4'h7: seg[6:0] = 7'b1111000;
            4'h8: seg[6:0] = 7'b0000000; 4'h9: seg[6:0] = 7'b0010000;
            default: seg[6:0] = 7'b1111111;
        endcase
        
        // 소수점 제어 (an[2] 위치에 고정)
        if (sel == 2'b10) seg[7] = dp_state; 
        else seg[7] = 1'b1; // 나머지 자리는 DP Off
    end

endmodule