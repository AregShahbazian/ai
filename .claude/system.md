# System Notes

## "Laptop slow" triage (do this first — 3 known causes below)
1. Don't trust single freq samples or System Monitor %. Run the busy-loop test:
   `for i in 1 2; do timeout 3 sh -c 'while :; do :; done' & sleep 2; cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq | sort -n | tail -1; wait; done`
   Healthy = peak ≥ 3–4 GHz. Stuck at ~400000 under load = hard cap → **Issue #3 (PROCHOT)**.
2. If idle is 400 MHz but load ramps up fine → `min_perf_pct` floor → **Issue #2**.
3. If `powerprofilesctl get` ≠ performance / errors → **Issue #1** (cpupower conflict).
User can't sudo from Claude's shell: give **one-liner** commands to paste in a
normal terminal (heredocs don't paste well). EC reset = shutdown, unplug, hold
power 20 s.

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

## Issue #3 — BD PROCHOT throttling to 400 MHz (2026-08-26)

### Symptom
Same look as #2 (`performance` reported, cores at 400 MHz) — but `min_perf_pct`
fix did **not** help, and cores stayed at 400 MHz **even under load**, with cool
temps (~60°C), on AC or battery, with thermald stopped. Readings intermittently
jump to 1.3–3.6 GHz, so single samples mislead. `fix-pstate.service` got
installed/enabled this day but was irrelevant to this issue.

### Root cause
**BD PROCHOT** asserted by the embedded controller. MSR `0x1B1` bit10 = PROCHOT
currently asserted (bit11 = it was asserted since last clear). MSR `0x1FC` bit0 is
only the BD-PROCHOT *enable* (normally 1 on laptops — not the problem itself).
Huawei MateBook VGHH-XX, Core Ultra 9 185H, BIOS 1.31 (2026-03-18).

### Diagnose (one-liner)
```bash
sudo modprobe msr && sudo python3 -c "import os,struct;v=struct.unpack('<Q',os.pread(os.open('/dev/cpu/0/msr',os.O_RDONLY),8,0x1B1))[0];print('PROCHOT asserted=%d  logged=%d'%(v>>10&1,v>>11&1))"; for i in 1 2; do timeout 3 sh -c 'while :; do :; done' & sleep 2; cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq | sort -n | tail -1; wait; done
```
Healthy: `asserted=0` and peak freq ≥ 3–4 GHz under load.
Also run a busy loop (`timeout 4 sh -c 'while :; do :; done'`) and read freqs —
if they stay at 400000 under load, it is a hard cap, not the pstate floor.

### Fix
1. **EC reset** (worked 2026-08-26): full shutdown, unplug AC, hold power 20 s,
   boot. Re-run diagnose — cores went from 400 MHz cap to 4.9 GHz under load.
2. Software override needs MSR writes, which **Secure Boot / kernel lockdown
   (`integrity`) blocks** (`Operation not permitted`). To use it: disable
   Secure Boot in BIOS, then clear bit0 of 0x1FC on all CPUs (boot service) — this *disables* BD PROCHOT
   so the EC can no longer throttle; risky if the EC ever asserts it for a real reason.
3. Check Huawei for a BIOS/EC update newer than 1.31.

Note: high CPU % in System Monitor during this state is a red herring — normal
desktop load just looks heavy at 400 MHz.
