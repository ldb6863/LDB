`timescale 1ns / 1ps

module bin2bcd(
    input [5:0] bin,      // 0~59 입력
    output reg [7:0] bcd  // {10의자리(4bit), 1의자리(4bit)}
);
    // 6비트 입력(0~59)은 10으로 나눈 몫과 나머지가 각각 BCD의 상/하위가 됨
    // 하드웨어 리소스 최적화를 위해 시프트 알고리즘 대신 
    // 가독성과 정확성이 높은 수식형으로 작성 (합성 시 최적화됨)
    
    always @(*) begin
        if (bin >= 6'd60) begin
            bcd = 8'h00; // 범위 초과 예외 처리
        end else begin
            // 10의 자리는 bin / 10
            // 1의 자리는 bin % 10
            bcd[7:4] = bin / 10;
            bcd[3:0] = bin % 10;
        end
    end
endmodule