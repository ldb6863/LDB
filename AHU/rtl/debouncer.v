`timescale 1ns / 1ps

module debouncer #(parameter DEBOUNCE_LIMIT = 20'd999_999) (
    input      clk,
    input      reset,
    input      noisy_btn,  // raw noisy button input
    output reg clean_btn
);
    reg [19:0] count;
    reg btn_state=0;

    always @(posedge clk or posedge reset) begin
        if (reset) begin   // active-high reset
            count <= 0;
            btn_state <= 0;
            clean_btn <= 0;
        end else if (noisy_btn == btn_state) begin  // 버튼 상태가 이전과 동일할 경우 (안정됨)
            count <= 0;
        end else begin
            if (count < DEBOUNCE_LIMIT)  // 버튼 상태가 바뀌었지만 아직 안정되지 않은 경우
                count <= count + 1;
            else begin  // 상태가 충분히 오랫동안 유지됨(10ms)
                btn_state <= noisy_btn;
                clean_btn <= noisy_btn;
                count <= 0;  // 리셋하면 다음 변경을 다시 감지할 수 있음
            end
        end
    end
endmodule
