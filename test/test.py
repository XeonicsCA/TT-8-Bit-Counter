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
    cocotb.start_soon(Clock(dut.clk, CLK_US, units="us").start())
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
async def load_turnaround_report(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_US, units="us").start())
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    EN_BIT, LOAD_REQBIT, DRIVE_BIT = 0, 1, 2
    ui = (1 << EN_BIT) | (1 << DRIVE_BIT)   # en=1, drive_en=1
    dut.ui_in.value = ui

    # request a load (one-cycle pulse)
    dut.ui_in.value = ui | (1 << LOAD_REQBIT)
    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = ui

    # RELEASE cycle (expected Hi-Z); present external data
    await ClockCycles(dut.clk, 1)
    dut._log.info(f"[load] RELEASE: time={cocotb.utils.get_sim_time('ns')}ns "
                  f"uio_oe={int(dut.uio_oe.value):#04x} uo_out={int(dut.uo_out.value)}")
    load_val = 0xA5
    dut.uio_in.value = load_val
    dut._log.info(f"[load]  external drives uio_in={load_val:#04x}")

    # CAPTURE cycle (DUT samples uio_in)
    await ClockCycles(dut.clk, 1)
    dut._log.info(f"[load] CAPTURE: time={cocotb.utils.get_sim_time('ns')}ns "
                  f"uio_oe={int(dut.uio_oe.value):#04x} uo_out={int(dut.uo_out.value)}")

    # Back to DRIVE
    await ClockCycles(dut.clk, 1)
    dut._log.info(f"[load] DRIVE again: uio_oe={int(dut.uio_oe.value):#04x} uo_out={int(dut.uo_out.value)}")

    # Let it run a few more cycles and log
    for i in range(3):
        await ClockCycles(dut.clk, 1)
        dut._log.info(f"[load] post-capture cycle {i+1}: "
                      f"uio_oe={int(dut.uio_oe.value):#04x} uo_out={int(dut.uo_out.value)}")

    # keep sim running for VCD
    await ClockCycles(dut.clk, 20)
    dut._log.info("End: load_turnaround_report")