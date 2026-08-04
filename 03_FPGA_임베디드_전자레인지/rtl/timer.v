module timer(
    input clk,
    input reset,
    input tick_1s,
    input timer_en,         // 카운트다운 활성화
    input timer_clr,        // 시간 초기화 명령
    input [2:0] timer_add,  // 시간 추가 명령 [0]:10s, [1]:30s, [2]:1m
    output [15:0] seg_data,
    output reg is_time_over
);
    reg [3:0] m10, m1, s10, s1;
    assign seg_data = {m10, m1, s10, s1};

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            {m10, m1, s10, s1} <= 16'h0000;
            is_time_over <= 1'b0;
        end else if (timer_clr) begin
            {m10, m1, s10, s1} <= 16'h0000;
            is_time_over <= 1'b0;
        end else begin
            // 1. 시간 추가 로직 (FSM의 명령에 따름)
            if (timer_add[0]) begin // +10s
                if (s10 == 5) begin s10 <= 0; m1 <= (m1==9)?0:m1+1; m10 <= (m1==9)?m10+1:m10; end
                else s10 <= s10 + 1;
                is_time_over <= 1'b0;
            end
            if (timer_add[1]) begin // +30s
                if (s10 >= 3) begin s10 <= s10-3; m1 <= (m1==9)?0:m1+1; m10 <= (m1==9)?m10+1:m10; end
                else s10 <= s10 + 3;
                is_time_over <= 1'b0;
            end
            if (timer_add[2]) begin // +1m
                if (m1 == 9) begin m1 <= 0; m10 <= m10 + 1; end
                else m1 <= m1 + 1;
                is_time_over <= 1'b0;
            end

            // 2. 카운트다운 로직
            if (tick_1s && timer_en) begin
                if ({m10, m1, s10, s1} == 16'h0001) begin
                    {m10, m1, s10, s1} <= 16'h0000;
                    is_time_over <= 1'b1;
                end else begin
                    if (s1 > 0) s1 <= s1 - 1;
                    else begin
                        s1 <= 9;
                        if (s10 > 0) s10 <= s10 - 1;
                        else begin
                            s10 <= 5;
                            if (m1 > 0) m1 <= m1 - 1;
                            else begin m1 <= 9; m10 <= m10 - 1; end
                        end
                    end
                end
            end
        end
    end
endmodule