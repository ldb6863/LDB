`timescale 1ns / 1ps

module uart_controller(
    input clk, reset,

    // 물리 핀
    input rx, output tx,

    // 1. 수신: 파서 결과 출력들 (유저님 & 팀원)
    output rtc_set_trigger,
    output [47:0] rtc_set_time_bcd,
    output rtc_set_alarm_trig,
    output [15:0] rtc_alarm_time_bcd,
    output [7:0] target_temp, target_temp_dec,

    // 2. 송신: 1초마다 보낼 통합 데이터 입력
    input unified_tx_trigger,     // 1초(1Hz) 틱 하나만 받으면 됨!
    input [47:0] current_time,
    input [7:0] dht_temp, dht_temp_dec,
    input [7:0] dht_humi, dht_humi_dec
);

    wire [7:0] w_rx_data, w_tx_data;
    wire w_rx_done, w_tx_busy, w_tx_start;

    // [1] 물리적 통신 모듈
    uart_rx #(.BPS(9600)) u_rx(
        .clk(clk), .reset(reset), .rx(rx), .data_out(w_rx_data), .rx_done(w_rx_done)
    );
    uart_tx #(.BPS(9600)) u_tx(
        .clk(clk), .reset(reset), .tx_data(w_tx_data), .tx_start(w_tx_start), .tx(tx), .tx_done(), .tx_busy(w_tx_busy)
    );

    // [2] 수신부: 귀는 하나, 뇌는 두 개! (기존과 동일)
    rtc_uart_parser u_rtc_parser(
        .clk(clk), .reset(reset), .rx_done(w_rx_done), .rx_data(w_rx_data), 
        .set_trigger(rtc_set_trigger), .set_time_bcd(rtc_set_time_bcd),
        .set_alarm_trig(rtc_set_alarm_trig), .alarm_time_bcd(rtc_alarm_time_bcd)
    );
    dht_uart_parser u_dht_parser(
        .clk(clk), .reset(reset), .rx_done(w_rx_done), .rx_data(w_rx_data),
        .target_temp(target_temp), .target_temp_dec(target_temp_dec)
    );

    // [3] 송신부: 통합 센더 하나로 끝!
    unified_data_sender u_sender(
        .clk(clk), .reset(reset),
        .data_valid(unified_tx_trigger), .tx_busy(w_tx_busy),
        .current_time(current_time),
        .temp(dht_temp), .temp_dec(dht_temp_dec),
        .humi(dht_humi), .humi_dec(dht_humi_dec),
        .tx_start(w_tx_start), .tx_data(w_tx_data)
    );

endmodule