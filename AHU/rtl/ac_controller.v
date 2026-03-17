`timescale 1ns / 1ps

module ac_controller(
    input clk,
    input reset,
    
    // --- [1단계 관문] FSM에서 판단한 시스템 활성화 신호 (초음파 OR 알람) ---
    input system_on,                 

    // --- [2단계 관문용] 온도 데이터 (DHT11 및 UART 목표가) ---
    input [7:0] cur_temp, cur_temp_dec,     
    input [7:0] tgt_temp, tgt_temp_dec,     

    // --- 출력 ---
    output ac_running,               // 현재 에어컨이 실제로 도는지 확인용 (LED 등 연결 가능)
    output motor_pwm,                // DC 모터 제어 신호
    output servo_pwm                 // 서보 모터 제어 신호
);

    localparam S_IDLE = 1'b0;
    localparam S_RUN  = 1'b1;

    reg state;
    reg r_ac_running;

    // 가동 상태를 외부(Top)에서 모니터링할 수 있도록 할당
    assign ac_running = r_ac_running;

    // =========================================================
    // 2단계 관문 로직: 온도 비교 (현재 온도 >= 목표 온도)
    // =========================================================
    wire temp_is_high = (cur_temp > tgt_temp) || 
                        ((cur_temp == tgt_temp) && (cur_temp_dec >= tgt_temp_dec));
                        
    // 최종 가동 조건: 1단계(system_on)도 1이고 AND 2단계(온도)도 높아야 함
    wire ac_on_cond = system_on && temp_is_high;

    // =========================================================
    // 상태 머신 (FSM)
    // =========================================================
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            state <= S_IDLE;
            r_ac_running <= 0;
        end else begin
            case (state)
                S_IDLE: begin
                    r_ac_running <= 0; 
                    // 두 관문을 모두 통과하면 가동 시작
                    if (ac_on_cond) begin
                        state <= S_RUN;        
                    end
                end

                S_RUN: begin
                    r_ac_running <= 1; 
                    // 조건 중 하나라도 깨지면(사람이 나가거나 시원해지면) 즉시 정지
                    if (!ac_on_cond) begin 
                        state <= S_IDLE;
                    end
                end
            endcase
        end
    end

    // =========================================================
    // DC 모터 (바람) & 서보 모터 (문 개폐) 제어 모듈 호출
    // =========================================================
    
    // 1. DC 모터 PWM 생성
    wire [16:0] w_duty_ticks = (r_ac_running) ? 17'd80_000 : 17'd0;

    pwm_gen #(.PWM_PERIOD(100_000), .RESOLUTION(17)) u_dc_pwm (
        .clk(clk), .reset(reset), 
        .en(r_ac_running),    // 가동 중일 때만 PWM 출력 [cite: 18]
        .duty(w_duty_ticks), .pwm_out(motor_pwm)   
    );

    // 2. 서보 모터 각도 제어
    servo_motor u_ac_door (
        .clk(clk), .reset(reset),
        .door_cmd(r_ac_running), // 1이면 열림, 0이면 닫힘 [cite: 19]
        .pwm_servo(servo_pwm)    
    );

endmodule
