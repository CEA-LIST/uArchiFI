module tb_addr;

  reg clk;
  reg [3:0] a_in, b_in;
  reg [3:0] a1_in, b1_in;
  reg c_in, c_in1;

  // Registered versions for delayed application
  reg [3:0] a_reg, b_reg;
  reg [3:0] a1_reg, b1_reg;
  reg c_in_reg, c_in1_reg;

  // DUT outputs
  wire [3:0] sum1, sum2;
  wire c_out1, c_out2;

  reg [2:0] cycle_cnt;
  reg       done;

  // Clock generation
  initial clk = 0;
  always #5 clk = ~clk;

  // Instantiate both DUTs
  (* keep *)
  addr dut1 (
      .clk(clk),
      .a(a_reg),
      .b(b_reg),
      .c_in(c_in_reg),
      .sum(sum1),
      .c_out(c_out1)
  );

  (* keep *)
  addr dut2 (
      .clk(clk),
      .a(a1_reg),
      .b(b1_reg),
      .c_in(c_in1_reg),
      .sum(sum2),
      .c_out(c_out2)
  );

  // Initial conditions
  initial begin
    cycle_cnt = 0;
    done      = 0;

    a_in      = 4'd2;
    b_in      = 4'd2;
    c_in      = 0;

    a1_in     = 4'd2;
    b1_in     = 4'd3;  // different input
    c_in1     = 0;

    // Reset all regs to zero
    a_reg     = 0;
    b_reg     = 0;
    a1_reg    = 0;
    b1_reg    = 0;
    c_in_reg  = 0;
    c_in1_reg = 0;
  end

  // Cycle control logic
  always @(posedge clk) begin
    cycle_cnt <= cycle_cnt + 1;

    case (cycle_cnt)
      // Cycle 1: do nothing (idle)
      3'd0: begin
        a_reg  <= 4'd0;
        b_reg  <= 4'd0;
        a1_reg <= 4'd0;
        b1_reg <= 4'd0;
      end

      // Cycle 2: store inputs, but not yet use them
      3'd1: begin
        a_reg  <= a_in;  // capture or register
        b_reg  <= b_in;
        a1_reg <= a1_in;
        b1_reg <= b1_in;
      end

      // Cycle 3: feed the stored values to adders (operating cycle)
      3'd2: begin
        a_reg  <= a_in;
        b_reg  <= b_in;
        a1_reg <= a1_in;
        b1_reg <= b1_in;
      end

      // Cycle 4: set done high to trigger the assertion
      3'd3: begin
        done <= 1;
      end
    endcase
  end

  // Assertion once computation done (Cycle 4)
  always @(posedge clk) begin
    assert property (!(done && ((sum1 == sum2))));
    //if (done) begin
    //  assert (!((sum1 == sum2) && (c_out1 == c_out2)));
    //end
  end

endmodule

