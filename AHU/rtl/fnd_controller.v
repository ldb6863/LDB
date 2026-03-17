`timescale 1ns / 1ps

module fnd_controller(
    input clk, reset,
    input mode_sel, 
    
    // --- 출력할 데이터 입력 ---
    input [47:0] current_time,  // RTC 시간
    input [7:0] dht_temp,       // DHT11 온도
    input [7:0] dht_humi,       // DHT11 습도
    
    // --- 물리적 FND 핀 연결 ---
    output [3:0] an,
    output [7:0] seg
);

    wire [3:0] w_rtc_an,  w_dht_an;
    wire [7:0] w_rtc_seg, w_dht_seg;

    // 1. 시계 화면 모듈
    rtc_fnd_control u_rtc_fnd (
        .clk(clk), 
        .reset(reset), 
        .current_time(current_time), 
        .an(w_rtc_an), 
        .seg(w_rtc_seg)
    );

    // 2. 온습도 화면 모듈
    dht_fnd_control u_dht_fnd (
        .clk(clk), 
        .reset(reset),
        .temp(dht_temp), 
        .humi(dht_humi), 
        .an(w_dht_an), 
        .seg(w_dht_seg)
    );

    // 3. 화면 전환 MUX (신호등 역할)
    // mode_sel이 1이면 온습도 화면, 0이면 시계 화면을 물리 핀으로 연결
    assign an  = mode_sel ? w_dht_an  : w_rtc_an;
    assign seg = mode_sel ? w_dht_seg : w_rtc_seg;

endmodule
