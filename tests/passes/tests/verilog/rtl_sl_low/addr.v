module addr (
    input  wire       clk,
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire       c_in,
    output reg  [3:0] sum,
    output reg        c_out
);

  always @(posedge clk) begin
    {c_out, sum} <= a + b + c_in;
  end

endmodule

