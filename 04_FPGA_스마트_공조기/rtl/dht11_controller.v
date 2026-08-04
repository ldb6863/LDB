`timescale 1ns / 1ps

module dht11_controller(
    input clk,
    input reset,
    inout dht11_pin,
    output wire [7:0] temp,       // 하위 모듈(dht11.v)과 연결할 wire
    output wire [7:0] temp_dec,
    output wire [7:0] humi,       // 하위 모듈과 연결할 wire
    output wire [7:0] humi_dec,
    output wire data_valid        // 하위 모듈과 연결할 wire
);

    wire w_tick_1s;

    // 1. 기존에 만들어둔 tick_gen 모듈을 사용하여 1초(1Hz) 신호 생성
    tick_gen #(
        .COUNT_MAX(100_000_000)   // 100MHz 기준 1초
    ) u_tick_1s (
        .clk(clk),
        .reset(reset),
        .tick(w_tick_1s)
    );

    // 2. FSM이 포함된 순수 센서 통신 모듈
    dht11 u_dht11 (
        .clk(clk),
        .reset(reset),
        .start_trigger(w_tick_1s), // 1초마다 통신 시작 트리거 발생
        .dht11_pin(dht11_pin),
        .temp(temp),
        .temp_dec(temp_dec),
        .humi(humi),
        .humi_dec(humi_dec),
        .data_valid(data_valid)
    );

endmodule
