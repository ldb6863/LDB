`timescale 1ns / 1ps

module rtc_fnd_control(
    input clk, reset,
    input [47:0] current_time, // {YY, MM, DD, hh, mm, ss}
    output reg [3:0] an,
    output reg [7:0] seg
);
    wire [3:0] hr_10 = current_time[23:20]; wire [3:0] hr_1 = current_time[19:16];
    wire [3:0] mi_10 = current_time[15:12]; wire [3:0] mi_1 = current_time[11:8];

    // 내부 1ms 틱
    wire tick_1ms;
    tick_gen #(.COUNT_MAX(100_000)) u_tick_1ms (.clk(clk), .reset(reset), .tick(tick_1ms));
    
    // DP(점) 깜빡임 제어를 위한 1Hz 틱 (0.5초 켜짐, 0.5초 꺼짐)
    wire tick_1hz;
    tick_gen #(.COUNT_MAX(100_000_000)) u_tick_1hz (.clk(clk), .reset(reset), .tick(tick_1hz));
    reg dp_state;
    always @(posedge clk or posedge reset) begin
        if (reset) dp_state <= 1;
        else if (tick_1hz) dp_state <= ~dp_state; 
    end

    reg [1:0] scan_cnt;
    always @(posedge clk, posedge reset) begin
        if (reset) scan_cnt <= 2'b00;
        else if (tick_1ms) scan_cnt <= scan_cnt + 1;
    end

    reg [3:0] current_digit;
    always @(*) begin
        case(scan_cnt)
            2'b00: begin an = 4'b1110; current_digit = mi_1;  end // an[0]: 분 1
            2'b01: begin an = 4'b1101; current_digit = mi_10; end // an[1]: 분 10
            2'b10: begin an = 4'b1011; current_digit = hr_1;  end // an[2]: 시 1
            2'b11: begin an = 4'b0111; current_digit = hr_10; end // an[3]: 시 10
            default: begin an = 4'b1111; current_digit = 4'd0; end
        endcase
    end

    always @(*) begin
        case(current_digit)
            4'd0: seg = 8'b1100_0000; 4'd1: seg = 8'b1111_1001; 4'd2: seg = 8'b1010_0100;
            4'd3: seg = 8'b1011_0000; 4'd4: seg = 8'b1001_1001; 4'd5: seg = 8'b1001_0010;
            4'd6: seg = 8'b1000_0010; 4'd7: seg = 8'b1111_1000; 4'd8: seg = 8'b1000_0000;
            4'd9: seg = 8'b1001_0000; default: seg = 8'b1111_1111;
        endcase
        
        // 시와 분 사이 an[2]에서 점(DP) 깜빡임
        if (scan_cnt == 2'b10) seg[7] = dp_state;
        else seg[7] = 1'b1;
    end
endmodule
