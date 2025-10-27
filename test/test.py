# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

CLK_US = 10  # 100 kHz like the template

@cocotb.test()
async def count_to_20(dut):
    dut._log.info("Starting count_to_20")

    # clock + reset
    cocotb.start_soon(Clock(dut.clk, CLK_US, unit="us").start())
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 5)   # hold reset
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

    # wait 20 clocks; expect uo_out == 20
    await ClockCycles(dut.clk, 20)
    assert int(dut.uo_out.value) == 20, f"expected 20, got {int(dut.uo_out.value)}"

@cocotb.test()
async def load_turnaround(dut):
    dut._log.info("Starting load_turnaround")

    cocotb.start_soon(Clock(dut.clk, CLK_US, unit="us").start())
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2) # hold reset
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    # enable counting and bus driving
    EN_BIT, LOAD_REQBIT, DRIVE_BIT = 0, 1, 2
    ui = 0
    ui = (1 << EN_BIT) | (1 << DRIVE_BIT)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 2) # wait 2 cycles before requesting load

    # put load vlaue on input lines
    load_val = 0xFA
    dut.uio_in.value = load_val

    # request a load (one-cycle pulse)
    ui |= (1 << LOAD_REQBIT)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 1)
    ui &= ~(1 << LOAD_REQBIT)
    dut.ui_in.value = ui
    await ClockCycles(dut.clk, 1)

    # RELEASE cycle: outputs should be Hi-Z; drive external data now
    await ClockCycles(dut.clk, 1)
    assert int(dut.uio_oe.value) == 0, "uio_oe should be 0 during RELEASE"

    # CAPTURE: value is latched into count after this cycle?
    await ClockCycles(dut.clk, 1)
    assert int(dut.uio_oe.value) == 0, "uio_oe should be 0 during CAPTURE"

    # Back to DRIVE, value is now latched into count and increment resumes
    await ClockCycles(dut.clk, 1)
    assert int(dut.uio_oe.value) == 0xFF, "uio_oe should re-enable after CAPTURE"
    assert int(dut.uo_out.value) == load_val, f"capture failed: got {int(dut.uo_out.value)}"
    
    # count for 10 cycles and check value, testing for counter wrap around
    await ClockCycles(dut.clk, 10)
    assert int(dut.uo_out.value) == ((load_val + 10) & 0xFF)
