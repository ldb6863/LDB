`timescale 1ns / 1ps

module shift_led(
    input clk,           // 100MHz
    input reset,
    input motor_en,      // FSM에서 오는 조리 중 신호
    output reg [15:0] led // Basys3의 LED 16개 전체
    );

    localparam SHIFT_TIME = 5_000_000; // 0.05초 속도
    reg [22:0] r_count;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_count <= 0;
            led <= 16'b1000_0000_0000_0000; // 맨 왼쪽(L15)부터 시작
        end else if (motor_en) begin
            if (r_count >= SHIFT_TIME - 1) begin
                r_count <= 0;
                // 오른쪽으로 시프트 (L15 -> L14 -> ... -> L0)
                if (led == 16'b0000_0000_0000_0001)
                    led <= 16'b1000_0000_0000_0000; // 끝에 도달하면 다시 맨 왼쪽으로
                else
                    led <= led >> 1;
            end else begin
                r_count <= r_count + 1;
            end
        end else begin
            r_count <= 0;
            led <= 16'b0;
            // 조리가 멈췄을 때 다음 시작을 위해 다시 왼쪽 끝으로 준비
            led <= 16'b1000_0000_0000_0000; 
        end
    end

endmodule