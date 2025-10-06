/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_example #(
  parameter DEFAULT_EN = 1'b1,    // count even if ui_in[0] == 0;
  parameter DEFAULT_DRIVE = 1'b1  // drive uio by default after reset
) (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
  // sync ui_in controls to clk
  logic [2:0] ctrl_q, ctrl_qq;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      ctrl_q <= '0;
      ctrl_qq <= '0;
    end
    else begin
      ctrl_q <= ui_in[2:0];
      ctrl_qq <= ctrl_q;    // one-cycle delayed copy
    end
  end

  wire en_lvl = ctrl_q[0];
  wire load_lvl = ctrl_q[1];
  wire oe_lvl = ctrl_q[2];

  wire en = DEFAULT_EN ? 1'b1 : en_lvl;
  wire load_pulse = load_lvl & ~ctrl_qq[1];        // rising-edge detection
  wire oe = DEFAULT_DRIVE ? 1'b1 : oe_lvl;

  // 3 state FSM sequence, 0=DRIVE, 1=RELEASE, 2=CAPTURE, then back to 0
  logic [1:0] seq;  // 0,1,2

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) seq <= 2'd0;
    else if (load_pulse) seq <= 2'd1;
    else if (seq == 1) seq <= 2'd2;
    else if (seq == 2) seq <= 2'd0;
  end

  // counter
  logic [7:0] count;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) count <= 8'h00;            // reset counter
    else if (seq == 2'd2) count <= uio_in; // if in capture state, read in uio_in
    else if (en) count <= count + 8'h01;   // increment counter
  end

  // output
  assign uo_out = count;
  assign uio_out = count;
  // tri-state control
  // drive output only when in drive state and output is enabled
  wire driving = (seq == 2'd0) & oe;
  assign uio_oe = driving ? 8'hFF : 8'h00;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, ui_in[7:3], 1'b0};     // concat and takes bitwise & (last bit set to 0, so always 0)

endmodule
