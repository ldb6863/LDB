`timescale 1ns / 1ps

module rotary(
    input clk, reset,
    input clean_s1, clean_s2, clean_key,
    output reg [5:0] time_val,  // 0~59까지만 담으므로 6비트면 충분
    output reg write_en      // 버튼이 눌렸을 때 DS1302 쓰기를 시작할 트리거
);

    reg [1:0] r_prev_state = 2'b00;
    reg [1:0] r_curr_state = 2'b00;
    reg [1:0] r_step = 2'b00;
    reg r_prev_key = 1'b0;

    // 1. 다이얼 회전 (0 ~ 59 카운터)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_prev_state <= 2'b00;
            r_curr_state <= 2'b00;
            time_val <= 6'd0; // 초기화
            r_step <= 2'b00;
        end else begin
            r_prev_state <= r_curr_state;
            r_curr_state <= {clean_s1, clean_s2};
            
            case ({r_prev_state, r_curr_state})
                // 한 방향 회전 (값 증가)
                4'b0010, 4'b1011, 4'b1101, 4'b0100: begin
                    if (r_step == 2'b11) begin    
                        if (time_val == 6'd59) time_val <= 6'd0; // 59 다음은 0
                        else time_val <= time_val + 1;
                    end
                    r_step <= r_step + 1;
                end
                
                // 반대 방향 회전 (값 감소)
                4'b0001, 4'b0111, 4'b1110, 4'b1000: begin
                    if (r_step == 2'b11) begin    
                        if (time_val == 6'd0) time_val <= 6'd59; // 0 아래는 59
                        else time_val <= time_val - 1;
                    end
                    r_step <= r_step + 1;
                end
            endcase
        end
    end

    // 2. 푸시 버튼 (설정 완료 트리거)
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_prev_key <= 1'b0;
            write_en <= 1'b0;
        end else begin
            r_prev_key <= clean_key;
            // Rising edge에서 딱 1클럭만 트리거 펄스 생성
            if (!r_prev_key && clean_key) write_en <= 1'b1;
            else write_en <= 1'b0;
        end
    end
endmodule