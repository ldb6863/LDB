module tick_gen #(parameter COUNT_MAX = 100_000)(
    input clk, 
    input reset,
    output reg tick 
);
    reg [$clog2(COUNT_MAX):0] count_reg;
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            count_reg <= 0;
            tick <= 0;
        end else begin
            if (count_reg == COUNT_MAX - 1) begin
                count_reg <= 0;
                tick <= 1;
            end else begin
                count_reg <= count_reg + 1;
                tick <= 0;
            end
        end
    end
endmodule