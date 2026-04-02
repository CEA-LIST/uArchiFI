module tb_addr;

  reg        clk;
  reg  [3:0] a;
  reg  [3:0] b;
  reg        c_in;
  wire [3:0] sum;
  wire       c_out;
  (* keep *)
  addr dut (
      .clk(clk),
      .a(a),
      .b(b),
      .c_in(c_in),
      .sum(sum),
      .c_out(c_out)
  );

  initial begin
    clk = 0;
    a = 1;
    b = 1;
    c_in = 0;
  end

endmodule

