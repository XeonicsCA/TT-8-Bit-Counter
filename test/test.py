# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

CLK_US = 10  # 100 kHz like the template

@cocotb.test()
async def count_to_50(dut):
    dut._log.info("Start")

    # clock + reset
    cocotb.start_soon(Clock(dut.clk, CLK_US, unit="us").start())
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2)   # hold reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    # enable counting and (optionally) bus driving
    EN_BIT      = 0
    LOAD_REQBIT = 1
    DRIVE_BIT   = 2

    ui = 0
    ui |= (1 << EN_BIT)      # en = 1
    ui |= (1 << DRIVE_BIT)   # drive_en = 1 (optional)
    dut.ui_in.value = ui

    # wait 50 clocks; expect uo_out == 50
    await ClockCycles(dut.clk, 50)
    assert int(dut.uo_out.value) == 50, f"expected 50, got {int(dut.uo_out.value)}"

@cocotb.test()
async def load_turnaround(dut):
    """Optional: tests your RELEASE->CAPTURE load micro-sequence."""
    cocotb.start_soon(Clock(dut.clk, CLK_US, unit="us").start())
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    EN_BIT, LOAD_REQBIT, DRIVE_BIT = 0, 1, 2
    ui = (1 << EN_BIT) | (1 << DRIVE_BIT)
    dut.ui_in.value = ui

    # Request a load (one-cycle pulse)
    ui |= (1 << LOAD_REQBIT)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 1)
    ui &= ~(1 << LOAD_REQBIT)
    dut.ui_in.value = ui

    # RELEASE cycle: outputs should be Hi-Z; drive external data now
    await ClockCycles(dut.clk, 1)
    assert int(dut.uio_oe.value) == 0, "uio_oe should be 0 during RELEASE"
    load_val = 0xA5
    dut.uio_in.value = load_val

    # CAPTURE: value should latch into count
    await ClockCycles(dut.clk, 1)
    assert int(dut.uo_out.value) == load_val, f"capture failed: got {int(dut.uo_out.value)}"

    # Back to DRIVE and increment resumes
    await ClockCycles(dut.clk, 1)
    assert int(dut.uio_oe.value) == 0xFF, "uio_oe should re-enable after CAPTURE"
    await ClockCycles(dut.clk, 1)
    assert int(dut.uo_out.value) == ((load_val + 1) & 0xFF)