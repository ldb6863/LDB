`timescale 1ns / 1ps

module top(
    input clk, reset,
    
    // --- 1. 스위치 및 버튼 ---
    input s1, s2, key,
    input [5:0] sw,     // sw[15]: 화면전환, sw[4:3]: 모드, sw[2:0]: 시간수정
    
    // --- 2. 통신 및 센서 핀 ---
    input RsRx,      
    output RsTx,     
    inout ds_io,    
    output ds_sclk, ds_ce,   
    inout dht11_pin,     // 팀원 DHT11 핀
    input echo,
    output trig,
    
    // --- 3. 디스플레이 및 알람 ---
    output [7:0] seg,
    output [3:0] an,
    output [15:0] led,
    
    // --- 4. 모터 제어 핀 ---
    output motor_pwm, // DC 모터 속도 (바람)
    output motor_in1, // DC 모터 방향 (정방향 고정)
    output motor_in2, // DC 모터 방향 
    output servo_pwm,  // 서보 모터 (에어컨 문)
    output a, b
);

    // ==========================================
    // 내부 공용 와이어 모음 (신경망)
    // ==========================================
    wire w_tick_1s;
    wire w_clean_s1, w_clean_s2, w_clean_key;
    wire [5:0] w_set_time_bin;
    wire [7:0] w_rotary_bcd;
    wire w_rotary_write_en;

    // DS1302 & RTC
    wire [7:0] w_cmd_byte, w_write_data, w_read_data;
    wire w_ds_start, w_ds_valid;
    wire [47:0] w_current_time, w_set_time_bcd;
    wire [15:0] w_alarm_time_bcd;
    wire w_set_trigger, w_set_alarm_trig, w_alarm_match;

    // 센서 & 제어
    wire [11:0] w_dist_cm;
    wire w_dht_valid;
    wire [7:0] w_raw_temp, w_raw_temp_dec, w_raw_humi, w_raw_humi_dec;
    wire [7:0] w_disp_temp, w_disp_humi, w_send_temp, w_send_temp_dec, w_send_humi, w_send_humi_dec;
    wire [7:0] w_target_temp, w_target_temp_dec;
    
    wire w_system_on;

    // ==========================================
    // [1] 시스템 공용 (타이머 & 입력장치)
    // ==========================================
    tick_gen #(.COUNT_MAX(100_000_000)) u_tick_1s (.clk(clk), .reset(reset), .tick(w_tick_1s));
    
    debouncer #(.DEBOUNCE_LIMIT(200_000)) u_s1_db (.clk(clk), .reset(reset), .noisy_btn(s1), .clean_btn(w_clean_s1));
    debouncer #(.DEBOUNCE_LIMIT(200_000)) u_s2_db (.clk(clk), .reset(reset), .noisy_btn(s2), .clean_btn(w_clean_s2));
    debouncer #(.DEBOUNCE_LIMIT(100_000)) u_key_db(.clk(clk), .reset(reset), .noisy_btn(key), .clean_btn(w_clean_key));

    rotary u_rotary (
        .clk(clk), .reset(reset), .clean_s1(w_clean_s1), .clean_s2(w_clean_s2), .clean_key(w_clean_key), 
        .time_val(w_set_time_bin), .write_en(w_rotary_write_en)
    );
    bin2bcd u_bin2bcd (.bin(w_set_time_bin), .bcd(w_rotary_bcd));

    // ==========================================
    // [2] 통신 통합 허브 (PC 통신)
    // ==========================================
    uart_controller u_uart_hub(
        .clk(clk), .reset(reset),
        .rx(RsRx), .tx(RsTx),
        // 수신 파싱 데이터
        .rtc_set_trigger(w_set_trigger), .rtc_set_time_bcd(w_set_time_bcd),
        .rtc_set_alarm_trig(w_set_alarm_trig), .rtc_alarm_time_bcd(w_alarm_time_bcd),
        .target_temp(w_target_temp), .target_temp_dec(w_target_temp_dec),
        // 송신 데이터
        .unified_tx_trigger(w_tick_1s),
        .current_time(w_current_time),
        .dht_temp(w_send_temp), .dht_temp_dec(w_send_temp_dec),
        .dht_humi(w_send_humi), .dht_humi_dec(w_send_humi_dec)
    );

    // ==========================================
    // [3] 센서 수집부 (DS1302, 초음파, DHT11)
    // ==========================================
    ds1302 #(.HALF_PERIOD(25)) u_ds1302 (
        .clk(clk), .reset(reset), .ds1302_start_trigger(w_ds_start), .cmd_byte(w_cmd_byte), 
        .write_data(w_write_data), .ds_io(ds_io), .ds_ce(ds_ce), .ds_sclk(ds_sclk), 
        .read_data(w_read_data), .valid(w_ds_valid)
    );

    ultrasonic_sensor u_ultrasonic (.clk(clk), .reset(reset), .echo(echo), .trig(trig), .distance_cm(w_dist_cm));

    dht11_controller u_dht11_ctrl(
        .clk(clk), .reset(reset), .dht11_pin(dht11_pin),
        .temp(w_raw_temp), .temp_dec(w_raw_temp_dec), 
        .humi(w_raw_humi), .humi_dec(w_raw_humi_dec), .data_valid(w_dht_valid)
    );

    // ==========================================
    // [4] 두뇌부 (FSM)
    // ==========================================
    dht11_fsm u_dht11_fsm(
        .clk(clk), .reset(reset), .dht_valid(w_dht_valid),
        .dht_temp(w_raw_temp), .dht_temp_dec(w_raw_temp_dec),
        .dht_humi(w_raw_humi), .dht_humi_dec(w_raw_humi_dec), .tx_busy(1'b0),
        .display_temp(w_disp_temp), .display_humi(w_disp_humi),
        .send_temp(w_send_temp), .send_temp_dec(w_send_temp_dec),
        .send_humi(w_send_humi), .send_humi_dec(w_send_humi_dec),
        .uart_start_trigger() // uart_controller 통합으로 미사용
    );

    rtc_fsm u_rtc_fsm (
        .clk(clk), .reset(reset), .edit_sel(sw[2:0]), 
        .uart_write_en(w_set_trigger), .uart_bcd_data(w_set_time_bcd),
        .rotary_write_en(w_rotary_write_en), .rotary_bcd_data(w_rotary_bcd), 
        .ds_valid(w_ds_valid), .ds_read_data(w_read_data),
        .cmd_byte(w_cmd_byte), .write_data(w_write_data), .ds1302_start_trigger(w_ds_start),
        .current_time(w_current_time),
        .set_alarm_trig(w_set_alarm_trig), .alarm_time_bcd(w_alarm_time_bcd), .alarm_match(w_alarm_match)
    );

    master_fsm u_master_fsm (
        .clk(clk), .reset(reset), .mode_sel(sw[4:3]), .set_time_trig(w_set_alarm_trig),
        .alarm_match(w_alarm_match), .dist_cm(w_dist_cm),
        .system_on(w_system_on)
    );

    // ==========================================
    // [5] 행동 제어부 (디스플레이, 부저, 모터)
    // ==========================================
    fnd_controller u_fnd_hub(
        .clk(clk), .reset(reset),
        .mode_sel(sw[5]), // 스위치 5번으로 시계/온습도 전환!
        .current_time(w_current_time),
        .dht_temp(w_disp_temp), .dht_humi(w_disp_humi),
        .an(an), .seg(seg)
    );

    assign motor_in1 = 1'b1; // 모터 정방향 회전
    assign motor_in2 = 1'b0;

    ac_controller u_ac_ctrl(
        .clk(clk), .reset(reset),
        .system_on(w_system_on),
        .cur_temp(w_send_temp), 
        .cur_temp_dec(w_send_temp_dec),
        .tgt_temp(w_target_temp), 
        .tgt_temp_dec(w_target_temp_dec), .ac_running(),
        .motor_pwm(motor_pwm), .servo_pwm(servo_pwm)
    );

    // LED 디버깅 매핑
    assign led[15]    = w_system_on;          // 15번: 공조기 가동 상태
    assign led[14:12] = sw[2:0];            // 스위치 상태
    assign led[11:8]  = w_set_time_bin[3:0];  // 로터리 값
    assign led[7:0]   = w_read_data;          // DS1302 읽기 데이터 확인용

    assign a = ds_io;
    assign b = ds_sclk;

endmodule