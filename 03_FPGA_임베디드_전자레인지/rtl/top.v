`timescale 1ns / 1ps

module top(
    input clk,
    input reset,
    input [5:0] btn, // [0]:10s, [1]:30s, [2]:1m, [3]:Start, [4]:Stop, [5]:Door

    output [3:0] an,
    output [7:0] seg,
    output pwm_dc,
    output motor_direction,
    output pwm_servo,
    output buzzer,
    output [15:0] led
    );

    // 신호 와이어 선언
    wire [5:0] w_clean_btn;
    wire w_tick_1ms, w_tick_1s, w_tick_500ms;
    wire w_timer_en, w_timer_clr, w_motor_en, w_door_pos;
    wire [2:0] w_timer_add;
    wire [15:0] w_seg_data;
    wire [2:0] w_melody_sel;
    wire [1:0] w_state;
    wire w_is_time_over;

    // 1. Debouncers (6개 버튼 통합 처리)
    debouncer u_db0(.clk(clk), .reset(reset), .noisy_btn(btn[0]), .clean_btn(w_clean_btn[0]));
    debouncer u_db1(.clk(clk), .reset(reset), .noisy_btn(btn[1]), .clean_btn(w_clean_btn[1]));
    debouncer u_db2(.clk(clk), .reset(reset), .noisy_btn(btn[2]), .clean_btn(w_clean_btn[2]));
    debouncer u_db3(.clk(clk), .reset(reset), .noisy_btn(btn[3]), .clean_btn(w_clean_btn[3]));
    debouncer u_db4(.clk(clk), .reset(reset), .noisy_btn(btn[4]), .clean_btn(w_clean_btn[4]));
    debouncer u_db5(.clk(clk), .reset(reset), .noisy_btn(btn[5]), .clean_btn(w_clean_btn[5]));

    // 2. Tick Generators
    tick_gen #(.COUNT_MAX(100_000)) u_tick_1ms (.clk(clk), .reset(reset), .tick(w_tick_1ms));
    tick_gen #(.COUNT_MAX(100_000_000)) u_tick_1s (.clk(clk), .reset(reset), .tick(w_tick_1s));
    tick_gen #(.COUNT_MAX(50_000_000)) u_tick_500ms (.clk(clk), .reset(reset), .tick(w_tick_500ms));

    // 3. FSM (모든 상태 결정의 주체)
    fsm u_fsm(
        .clk(clk), 
        .reset(reset), 
        .tick_1ms(w_tick_1ms),
        .btn_start(w_clean_btn[3]), .btn_stop(w_clean_btn[4]), .btn_door(w_clean_btn[5]),
        .btn_10s(w_clean_btn[0]), .btn_30s(w_clean_btn[1]), .btn_1m(w_clean_btn[2]),
        .is_time_over(w_is_time_over), 
        .seg_data(w_seg_data),
        .timer_en(w_timer_en), .timer_clr(w_timer_clr), .timer_add(w_timer_add),
        .motor_en(w_motor_en), .door_pos(w_door_pos), .melody_sel(w_melody_sel),
        .out_state(w_state)
    );

    // 4. Timer (데이터 계산 모듈)
    timer u_timer(
        .clk(clk), 
        .reset(reset), 
        .tick_1s(w_tick_1s),
        .timer_en(w_timer_en), 
        .timer_clr(w_timer_clr), 
        .timer_add(w_timer_add),
        .seg_data(w_seg_data), 
        .is_time_over(w_is_time_over)
    );

    // 5. FND Control (상태 기반 디스플레이)
    fnd_control u_fnd_control(
        .clk(clk), 
        .reset(reset), 
        .tick_1ms(w_tick_1ms), 
        .tick_1s(w_tick_1s), 
        .tick_500ms(w_tick_500ms),
        .curr_state(w_state), 
        .seg_data(w_seg_data), 
        .an(an), 
        .seg(seg)
    );

    // 6. Actuators (FSM 명령에만 반응)
    dc_motor u_dc_motor(
        .clk(clk), 
        .reset(reset), 
        .motor_en(w_motor_en), 
        .pwm_dc(pwm_dc), 
        .motor_direction(motor_direction)
    );

    servo_motor u_servo_motor(
        .clk(clk), 
        .reset(reset), 
        .door_cmd(w_door_pos), 
        .pwm_servo(pwm_servo)
    );

    play_melody u_play_melody (
        .clk(clk), 
        .reset(reset), 
        .melody_sel(w_melody_sel), 
        .buzzer(buzzer)
    );

    shift_led u_shift_led(
        .clk(clk), 
        .reset(reset), 
        .motor_en(w_motor_en), 
        .led(led)
    );

endmodule