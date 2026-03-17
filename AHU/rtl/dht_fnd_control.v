`timescale 1ns / 1ps

module dht_fnd_control(
    input clk,
    input reset,
    input [7:0] temp, // 온도 (an[1], an[0]에 출력)
    input [7:0] humi, // 습도 (an[3], an[2]에 출력)
    output reg [3:0] an,
    output reg [7:0] seg
);

    // 1. 값 분리 (온도/습도를 10의 자리와 1의 자리로 분리)
    wire [3:0] temp_10s = (temp % 100) / 10;
    wire [3:0] temp_1s  = temp % 10;
    wire [3:0] humi_10s = (humi % 100) / 10;
    wire [3:0] humi_1s  = humi % 10;

    // 2. 1ms(1kHz) Tick 생성 (잔상효과 및 DP 타이머용)
    wire tick_1ms;
    tick_gen #(
        .COUNT_MAX(100_000) // 100MHz / 100,000 = 1kHz (1ms)
    ) u_tick_1ms (
        .clk(clk), 
        .reset(reset),
        .tick(tick_1ms) 
    );

    // 3. 온습도 값 변경 감지 및 DP 깜빡임 로직 (0.5초 동안 점등)
    reg [7:0] prev_temp, prev_humi;
    reg [9:0] dp_blink_timer; 
    reg dp_state; // 1: DP 끄기, 0: DP 켜기 (Active Low)

    always @(posedge clk, posedge reset) begin
        if (reset) begin
            prev_temp <= 8'd0;
            prev_humi <= 8'd0;
            dp_state <= 1'b1;     // DP 초기상태: 끄기
            dp_blink_timer <= 0;
        end else begin
            // 온습도 값이 이전과 다르면 500ms 깜빡임 타이머 시작
            if ((temp != prev_temp) || (humi != prev_humi)) begin
                prev_temp <= temp;
                prev_humi <= humi;
                dp_state <= 1'b0;          // DP 켜기 (0이 켜짐)
                dp_blink_timer <= 10'd500; // 1ms * 500 = 0.5초
            end 
            // 타이머 감소 및 DP 끄기
            else if (tick_1ms && (dp_blink_timer > 0)) begin
                dp_blink_timer <= dp_blink_timer - 1;
                if (dp_blink_timer == 1) begin
                    dp_state <= 1'b1;      // 0.5초가 지나면 다시 DP 끄기
                end
            end
        end
    end

    // 4. 자리수 선택용 2비트 카운터 (1ms마다 증가)
    reg [1:0] scan_cnt;
    always @(posedge clk, posedge reset) begin
        if(reset) scan_cnt <= 2'b00;
        else if(tick_1ms) scan_cnt <= scan_cnt + 1;
    end

    // 5. 스캔 카운터에 따라 표시할 숫자와 an 제어
    reg [3:0] current_digit;
    always @(*) begin
        case(scan_cnt)
            2'b00: begin an = 4'b1110; current_digit = temp_1s;  end // an[0]: 온도 1의 자리
            2'b01: begin an = 4'b1101; current_digit = temp_10s; end // an[1]: 온도 10의 자리
            2'b10: begin an = 4'b1011; current_digit = humi_1s;  end // an[2]: 습도 1의 자리
            2'b11: begin an = 4'b0111; current_digit = humi_10s; end // an[3]: 습도 10의 자리
            default: begin an = 4'b1111; current_digit = 4'd0; end
        endcase
    end

    // 6. 숫자를 7-Segment 신호로 변환 (seg[7]은 DP 제어)
    always @(*) begin
        // 기본 세그먼트 디코딩 (0이 불 켜짐)
        case(current_digit)
            4'd0: seg = 8'b1100_0000;
            4'd1: seg = 8'b1111_1001;
            4'd2: seg = 8'b1010_0100;
            4'd3: seg = 8'b1011_0000;
            4'd4: seg = 8'b1001_1001;
            4'd5: seg = 8'b1001_0010;
            4'd6: seg = 8'b1000_0010;
            4'd7: seg = 8'b1111_1000;
            4'd8: seg = 8'b1000_0000;
            4'd9: seg = 8'b1001_0000;
            default: seg = 8'b1111_1111;
        endcase
        
        // an[2] 자리(습도 1의 자리)가 켜질 때만 DP 깜빡임 상태(dp_state)를 적용
        if (scan_cnt == 2'b10) begin
            seg[7] = dp_state; 
        end else begin
            seg[7] = 1'b1; // 나머지 자리의 DP는 항상 끄기 (1이 꺼짐)
        end
    end
endmodule