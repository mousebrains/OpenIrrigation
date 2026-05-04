#! /usr/bin/env python3
#
# Estimate SD-card wear from /proc/uptime and /proc/diskstats.
#
# Defaults assume a SanDisk Industrial XI 64 GB (96 TBW rated, pSLC).
# Reports are based on host writes since the last boot, so the rate is
# only meaningful after the system has been up at least a few days.
#
# May-2026, Pat Welch, pat@mousebrains.com
#
import argparse
from pathlib import Path

SECTOR_BYTES = 512

def readUptimeSeconds() -> float:
  return float(Path("/proc/uptime").read_text().split()[0])

def readDiskstats(device: str) -> tuple[int, int]:
  # Returns (sectors_read, sectors_written) for the named device.
  for line in Path("/proc/diskstats").read_text().splitlines():
    f = line.split()
    if len(f) >= 11 and f[2] == device:
      return int(f[5]), int(f[9])
  raise SystemExit(f"{device} not found in /proc/diskstats")

parser = argparse.ArgumentParser(description="Estimate SD-card wear from kernel counters")
parser.add_argument("--device", default="mmcblk0", help="block device name (default mmcblk0)")
parser.add_argument("--tbw", type=float, default=96.0,
                    help="rated TBW in TB (default 96 = SanDisk Industrial XI 64 GB)")
parser.add_argument("--wa", type=float, default=3.0,
                    help="assumed write amplification factor (default 3)")
args = parser.parse_args()

uptime = readUptimeSeconds()
sectorsRead, sectorsWritten = readDiskstats(args.device)

days = uptime / 86400
gbRead = sectorsRead * SECTOR_BYTES / 1e9
gbWritten = sectorsWritten * SECTOR_BYTES / 1e9
gbPerDay = gbWritten / days if days > 0 else 0.0
gbPerYear = gbPerDay * 365
tbwGB = args.tbw * 1000
pctPerYear = gbPerYear / tbwGB * 100 if tbwGB > 0 else 0.0
yearsToTBW = tbwGB / gbPerYear if gbPerYear > 0 else float("inf")

print(f"Device:        {args.device}")
print(f"Uptime:        {days:.2f} days ({uptime/3600:.1f} h)")
print(f"Read:          {gbRead:.2f} GB since boot")
print(f"Written:       {gbWritten:.2f} GB since boot")
print(f"Rate:          {gbPerDay:.2f} GB/day")
print(f"Annualized:    {gbPerYear:.1f} GB/year")
print(f"Rated TBW:     {args.tbw:g} TB")
print(f"Host writes:   {pctPerYear:.4f} %/year of TBW ({yearsToTBW:.0f} y to TBW)")
print(f"With {args.wa:g}x WA:  {pctPerYear*args.wa:.4f} %/year ({yearsToTBW/args.wa:.0f} y to TBW)")

if days < 7:
  print()
  print(f"NOTE: only {days:.2f} days of uptime — early-boot writes inflate the rate.")
  print("      Re-run after at least a week of uptime for a steady-state estimate.")
