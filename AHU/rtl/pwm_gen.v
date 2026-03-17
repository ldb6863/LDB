`timescale 1ns / 1ps

module pwm_gen #(
    // 기본값은 서보모터(50Hz, 20ms) 기준으로 세팅
    parameter PWM_PERIOD = 2_000_000, 
    parameter RESOLUTION = 21         // 2,000,000을 담으려면 21비트 필요
)(
    input clk,
    input reset,
    input en,                             // 1일 때만 PWM 출력 (진동 방지용)
    input [RESOLUTION-1:0] duty,          // HIGH를 유지할 클럭 틱 수
    output reg pwm_out
);
    reg [RESOLUTION-1:0] count;
    
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count <= 0;
            pwm_out <= 0;
        end else begin
            // 1. 주기 카운터
            if (count >= PWM_PERIOD - 1) count <= 0;
            else count <= count + 1;
            
            // 2. Enable 상태일 때만 Duty 비율에 맞춰 PWM 출력
            if (en && (count < duty)) pwm_out <= 1;
            else pwm_out <= 0;
        end
    end
endmodule