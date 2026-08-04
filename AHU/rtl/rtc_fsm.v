`timescale 1ns / 1ps

module rtc_fsm(
    input clk, reset,
    
    input [2:0] edit_sel, 
    input rotary_write_en,          
    input [7:0] rotary_bcd_data,   
    
    input uart_write_en,
    input [47:0] uart_bcd_data,

    input ds_valid,             
    input [7:0] ds_read_data,
    output reg [7:0] cmd_byte,
    output reg [7:0] write_data,
  
    output reg ds1302_start_trigger,
    
    output reg [47:0] current_time,
    
    // 새로 추가된 알람 연동 포트
    input set_alarm_trig,
    input [15:0] alarm_time_bcd,
    output alarm_match
);

    // ==========================================
    // 알람 기능
    // ==========================================
    reg [15:0] r_alarm_reg;
    reg r_alarm_en; // 알람 활성화 깃발

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_alarm_reg <= 16'h0000;
            r_alarm_en <= 1'b0;
        end else if (set_alarm_trig) begin
            r_alarm_reg <= alarm_time_bcd;
            r_alarm_en <= 1'b1; // 명령어가 들어오면 알람 활성화
        end
    end
    
    // 알람이 켜져 있고(r_alarm_en), 현재 시간의 시/분(23:8)이 일치할 때만 트리거
    assign alarm_match = r_alarm_en && (current_time[23:8] == r_alarm_reg);


    // ==========================================
    // FSM 영역
    // ==========================================
    localparam S_INIT = 0, S_IDLE = 1, S_READ = 2, S_UART_WRITE = 3, S_ROTARY_WRITE = 4, S_WAIT = 5, S_RELAX = 6;
    reg [2:0] r_state;
    reg [23:0] r_delay_cnt;
    reg [7:0] r_relax_cnt; // 휴식 타이머
    
    reg [2:0] r_seq_idx;
    reg r_is_writing;
    
    reg r_uart_pending;
    reg r_rotary_pending;
    reg [47:0] r_latched_uart_data;
    reg [7:0] r_latched_rotary_data;

    // DS1302 주소 배열
    wire [7:0] addr_read [0:5];
    assign addr_read[0]=8'h81; assign addr_read[1]=8'h83; assign addr_read[2]=8'h85;
    assign addr_read[3]=8'h87; assign addr_read[4]=8'h89; assign addr_read[5]=8'h8D;

    wire [7:0] addr_write [0:5];
    assign addr_write[0]=8'h80; assign addr_write[1]=8'h82; assign addr_write[2]=8'h84;
    assign addr_write[3]=8'h86; assign addr_write[4]=8'h88; assign addr_write[5]=8'h8C;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            r_state <= S_INIT;
            ds1302_start_trigger <= 0; r_seq_idx <= 0;
            r_uart_pending <= 0; r_rotary_pending <= 0; current_time <= 48'd0;
        end else begin
            if (uart_write_en) begin
                r_uart_pending <= 1;
                r_latched_uart_data <= uart_bcd_data;
            end
            if (rotary_write_en) begin
                r_rotary_pending <= 1;
                r_latched_rotary_data <= rotary_bcd_data;
            end
            
            case (r_state)
                S_INIT: begin 
                    cmd_byte <= 8'h8E;
                    write_data <= 8'h00; // WP 해제
                    ds1302_start_trigger <= 1;
                    r_is_writing <= 1;
                    r_seq_idx <= 5;
                    r_state <= S_WAIT;
                end
                
                S_IDLE: begin
                    ds1302_start_trigger <= 0;
                    if (r_uart_pending) begin
                        r_uart_pending <= 0;
                        r_seq_idx <= 0; r_state <= S_UART_WRITE;
                    end else if (r_rotary_pending) begin
                        r_rotary_pending <= 0;
                        r_state <= S_ROTARY_WRITE;
                    end else if (r_delay_cnt >= 24'd10_000_000) begin 
                        r_delay_cnt <= 0;
                        r_seq_idx <= 0; r_state <= S_READ;
                    end else begin
                        r_delay_cnt <= r_delay_cnt + 1;
                    end
                end
                
                S_READ: begin 
                    cmd_byte <= addr_read[r_seq_idx];
                    ds1302_start_trigger <= 1; r_is_writing <= 0;
                    r_state <= S_WAIT;
                end
                
                S_UART_WRITE: begin 
                    cmd_byte <= addr_write[r_seq_idx];
                    ds1302_start_trigger <= 1; r_is_writing <= 1;
                    case(r_seq_idx)
                        0: write_data <= r_latched_uart_data[7:0];
                        1: write_data <= r_latched_uart_data[15:8];  
                        2: write_data <= r_latched_uart_data[23:16]; 
                        3: write_data <= r_latched_uart_data[31:24]; 
                        4: write_data <= r_latched_uart_data[39:32]; 
                        5: write_data <= r_latched_uart_data[47:40];
                    endcase
                    r_state <= S_WAIT;
                end
                
                S_ROTARY_WRITE: begin 
                    if (edit_sel <= 3'd5) cmd_byte <= addr_write[edit_sel];
                    else cmd_byte <= addr_write[0]; 
                    
                    write_data <= r_latched_rotary_data;
                    ds1302_start_trigger <= 1; r_is_writing <= 1; 
                    r_seq_idx <= 5; 
                    r_state <= S_WAIT;
                end
                
                S_WAIT: begin
                    ds1302_start_trigger <= 0;
                    if (ds_valid) begin
                        if (!r_is_writing) begin
                            case(r_seq_idx)
                                0: current_time[7:0]   <= ds_read_data;
                                1: current_time[15:8]  <= ds_read_data;
                                2: current_time[23:16] <= ds_read_data;
                                3: current_time[31:24] <= ds_read_data;
                                4: current_time[39:32] <= ds_read_data;
                                5: current_time[47:40] <= ds_read_data;
                            endcase
                        end
                        
                        if (r_seq_idx == 5) r_state <= S_IDLE;
                        else begin
                            r_seq_idx <= r_seq_idx + 1;
                            r_relax_cnt <= 0;
                            r_state <= S_RELAX; // 바로 다음 통신으로 안 가고 휴식 상태로 진입
                        end
                    end
                end
                
                S_RELAX: begin
                    // tCWH 규약 방어: 통신과 통신 사이 2us(200클럭) 동안 칩을 쉬게 해줌
                    if (r_relax_cnt >= 200) begin
                        r_state <= r_is_writing ? S_UART_WRITE : S_READ;
                    end else begin
                        r_relax_cnt <= r_relax_cnt + 1;
                    end
                end
                
                default: r_state <= S_INIT;
            endcase
        end
    end
endmodule