`timescale 1ns / 1ps

module servo_motor(
    input  clk,
    input  reset,
    input  door_cmd,    // 0:Close, 1:Open
    output pwm_servo    // 실제 핀으로 나가는 펄스
);
    // 1. 명령 변화 감지
    reg r_door_cmd_old;
    always @(posedge clk or posedge reset) begin
        if (reset) r_door_cmd_old <= 1'b0;
        else       r_door_cmd_old <= door_cmd;
    end
    wire w_cmd_changed = door_cmd ^ r_door_cmd_old;

    // 2. 작동 타이머 제어 (0.6초)
    reg [25:0] r_active_cnt;
    wire w_is_moving = (r_active_cnt > 0);

    always @(posedge clk or posedge reset) begin
        if (reset) r_active_cnt <= 0;
        else if (w_cmd_changed) r_active_cnt <= 9'd500;//r_active_cnt <= 26'd60_000_000;
        else if (w_is_moving)   r_active_cnt <= r_active_cnt - 1'b1;
    end

    // 3. 듀티 사이클 결정 (1ms or 2ms)
    wire [20:0] w_duty_value = (door_cmd) ? 5'd20 : 4'd10;//21'd200_000 : 21'd100_000;

    // 4. 만능 pwm_gen 인스턴스화 (서보모터용 셋업)
    pwm_gen #(
        .PWM_PERIOD(2_000_000), // 20ms
        .RESOLUTION(21)
    ) u_servo_pwm (
        .clk(clk),
        .reset(reset),
        .en(w_is_moving),       // 0.6초 타이머가 도는 동안만 Enable! (진동 방지)
        .duty(w_duty_value),    // 100,000 또는 200,000
        .pwm_out(pwm_servo)
    );
endmodule

// `timescale 1ns / 1ps

// module servo_motor(
//     input  clk,
//     input  reset,
//     input  door_cmd,    // FSM에서 결정된 문 상태 (0:Close, 1:Open)
//     output reg pwm_servo    
// );
//     // --- 1. 명령 변화 감지 (Edge Detection) ---
//     reg  r_door_cmd_old;
//     always @(posedge clk or posedge reset) begin
//         if (reset) r_door_cmd_old <= 1'b0;
//         else       r_door_cmd_old <= door_cmd;
//     end

//     // 문 상태 명령이 바뀌었을 때 (0->1 또는 1->0)
//     wire w_cmd_changed = door_cmd ^ r_door_cmd_old;

//     // --- 2. 작동 타이머 제어 (진동 방지) ---
//     reg [25:0] r_active_cnt;
//     wire w_is_moving = (r_active_cnt > 0);

//     always @(posedge clk or posedge reset) begin
//         if (reset) begin
//             r_active_cnt <= 0;
//         end else if (w_cmd_changed) begin
//             r_active_cnt <= 26'd60_000_000; // 명령 변경 시 0.6초간 타이머 시작
//         end else if (w_is_moving) begin
//             r_active_cnt <= r_active_cnt - 1'b1;
//         end
//     end

//     // --- 3. PWM 주기 생성 (50Hz, 20ms) ---
//     reg [20:0] r_pwm_cnt;
//     always @(posedge clk or posedge reset) begin
//         if (reset) r_pwm_cnt <= 21'd0;
//         else if (r_pwm_cnt >= 21'd2_000_000 - 1) r_pwm_cnt <= 21'd0;
//         else r_pwm_cnt <= r_pwm_cnt + 1'b1; 
//     end

//     // --- 4. 듀티 사이클 결정 ---
//     wire [19:0] w_duty_value = (door_cmd) ? 20'd200_000 : 20'd100_000;

//     // --- 5. PWM 출력 제어 ---
//     always @(posedge clk or posedge reset) begin
//         if (reset) begin
//             pwm_servo <= 1'b0; 
//         end else if (w_is_moving) begin
//             pwm_servo <= (r_pwm_cnt < w_duty_value) ? 1'b1 : 1'b0;
//         end else begin
//             pwm_servo <= 1'b0; // 0.6초가 지나면 펄스 차단 (진동 방지)
//         end
//     end
// endmodule