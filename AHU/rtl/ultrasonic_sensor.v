`timescale 1ns / 1ps

module ultrasonic_sensor(
    input clk, reset,
    input echo,
    output reg trig,
    output reg [11:0] distance_cm
);
    parameter MEASURE_PERIOD = 6_000_000; // 약 60ms 주기
    parameter TRIG_10US = 1_000;          // 10us

    reg [22:0] r_period_cnt;
    reg r_echo_d;

    // 나누기 연산 제거를 위한 카운터
    reg [12:0] r_cm_tick;
    reg [11:0] r_temp_dist;

    // 1. Trig 신호 생성
    always @(posedge clk or posedge reset) begin
        if (reset) begin r_period_cnt <= 0; trig <= 0; end 
        else begin
            if (r_period_cnt < MEASURE_PERIOD) begin
                r_period_cnt <= r_period_cnt + 1;
                trig <= (r_period_cnt < TRIG_10US) ? 1'b1 : 1'b0;
            end else r_period_cnt <= 0;
        end
    end

    // 2. 타이밍 에러 없는 거리 계산
    always @(posedge clk or posedge reset) begin
        if (reset) begin 
            r_echo_d <= 0; distance_cm <= 0; 
            r_temp_dist <= 0; r_cm_tick <= 0; 
        end 
        else begin
            r_echo_d <= echo;
            
            if (echo) begin
                // 5882 클럭(약 58.82us)마다 1cm씩 증가
                if (r_cm_tick == 13'd5881) begin
                    r_cm_tick <= 0;
                    r_temp_dist <= r_temp_dist + 1;
                end else begin
                    r_cm_tick <= r_cm_tick + 1;
                end
            end else if (r_echo_d && !echo) begin
                // Echo가 떨어지는 순간(Falling Edge)에 최종 거리를 출력에 반영
                distance_cm <= r_temp_dist;
            end else if (!echo) begin
                // 다음 측정을 위해 임시 변수 초기화
                r_temp_dist <= 0;
                r_cm_tick <= 0;
            end
        end
    end
endmodule

// `timescale 1ns / 1ps

// module ultrasonic_sensor(
//     input clk, reset,
//     input echo,
//     output reg trig,
//     output reg [11:0] distance_cm
// );
//     parameter MEASURE_PERIOD = 6_000_000; // 약 60ms 주기
//     parameter TRIG_10US = 1_000;          // 10us

//     reg [22:0] r_period_cnt;
//     reg [19:0] r_echo_cnt;
//     reg r_echo_d;

//     always @(posedge clk or posedge reset) begin
//         if (reset) begin r_period_cnt <= 0; trig <= 0; end 
//         else begin
//             if (r_period_cnt < MEASURE_PERIOD) begin
//                 r_period_cnt <= r_period_cnt + 1;
//                 trig <= (r_period_cnt < TRIG_10US) ? 1'b1 : 1'b0;
//             end else r_period_cnt <= 0;
//         end
//     end

//     always @(posedge clk or posedge reset) begin
//         if (reset) begin r_echo_cnt <= 0; r_echo_d <= 0; distance_cm <= 0; end 
//         else begin
//             r_echo_d <= echo;
//             if (echo) r_echo_cnt <= r_echo_cnt + 1;
//             else if (r_echo_d && !echo) begin
//                 distance_cm <= r_echo_cnt / 5882; // cm 변환
//                 r_echo_cnt <= 0;
//             end
//         end
//     end
// endmodule
