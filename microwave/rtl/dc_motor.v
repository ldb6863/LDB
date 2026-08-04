`timescale 1ns / 1ps

module dc_motor(
    input clk, reset,
    input motor_en, // FSM이 결정한 동작 신호
    output pwm_dc,
    output motor_direction
);
    reg [3:0] r_cnt;
    always @(posedge clk or posedge reset) begin
        if (reset) r_cnt <= 0;
        else r_cnt <= (r_cnt >= 9) ? 0 : r_cnt + 1;
    end

    // FSM이 허락(en)할 때만 PWM 출력
    assign pwm_dc = (motor_en && (r_cnt < 7)) ? 1'b1 : 1'b0;
    assign motor_direction = 1'b1;
endmodule