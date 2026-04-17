# System Notes

## Power Profile Issue (2026-02-25)

### Problem
Laptop was slow. CPU scaling governor showed `performance` (via `cpupower`), but
`powerprofilesctl get` revealed the system was actually stuck on `power-saver`.

### Root Cause
Two separate power management systems were conflicting:
- **`cpupower`** — sets the CPU governor directly (`scaling_governor`)
- **`power-profiles-daemon`** — higher-level service that GNOME UI talks to, also
  controls Intel P-state energy preferences, turbo boost, etc.

Using `cpupower frequency-set -g performance` locked the CPU driver, preventing
`power-profiles-daemon` from switching modes. So even though the governor said
"performance", all the other power-saving settings remained active.

The conflict also caused `powerprofilesctl set performance` to fail with:
```
Error writing 'energy_performance_preference': Device or resource busy
```

### Fix
1. Reset cpupower: `sudo cpupower frequency-set -g powersave`
2. Restart daemon: `sudo systemctl restart power-profiles-daemon`
3. Set profile properly: `powerprofilesctl set performance`

### Rule
Never mix `cpupower` and `powerprofilesctl`. Use only `powerprofilesctl` (or the
GNOME Settings > Power UI) to change power modes.

## Power Profile Issue #2 — min_perf_pct stuck after reboot (2026-02-25)

### Problem
After reboot, system was slow again. `powerprofilesctl get` reported `performance`
and `energy_performance_preference` was correctly set to `performance` on all CPUs,
but the system felt completely downthrottled.

### Root Cause
`/sys/devices/system/cpu/intel_pstate/min_perf_pct` was stuck at **8%**, capping all
CPUs to ~400 MHz. The `power-profiles-daemon` was not properly applying this value on
boot despite reporting "performance" mode. Likely a race condition at startup.

### Diagnosis
With `intel_pstate` driver, the `scaling_governor` showing `powersave` is **normal**
— it does NOT mean the CPU is throttled. The actual indicators to check are:
- `scaling_cur_freq` — actual current frequency (was stuck at 400 MHz)
- `min_perf_pct` — minimum performance floor (was 8%, should be higher)
- `energy_performance_preference` — per-CPU preference (was correctly `performance`)

### Fix
```bash
sudo sh -c 'echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct'
sudo systemctl restart power-profiles-daemon
powerprofilesctl set performance
```

### Permanent Fix
Create a systemd service to force `min_perf_pct` on every boot:
```bash
sudo tee /etc/systemd/system/fix-pstate.service << 'EOF'
[Unit]
Description=Fix intel_pstate min_perf_pct
After=power-profiles-daemon.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo 100 > /sys/devices/system/cpu/intel_pstate/min_perf_pct'

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable fix-pstate.service
```
