module tricky_example (
    input  wire [15:0] sig_b,
    input  wire        sel,
    output wire [16:0] sig_a
);

  // Lower bits are independent
  assign sig_a[15:0] = sig_b;

  // Upper bit depends on previous bit
  assign sig_a[16]   = sig_a[15] & sig_b[0];

endmodule
