#!/bin/sh
# Print what the numbers were measured on. `bench/run.py` collects most of this
# itself; this script is for a one-off record in RESULTS.md's header or a bug
# report.
set -e

echo "### Machine"
printf '%-14s %s\n' OS "$(uname -srm)"
[ -r /etc/os-release ] && printf '%-14s %s\n' Distro "$(. /etc/os-release && echo "$PRETTY_NAME")"
printf '%-14s %s\n' CPU "$(awk -F': ' '/model name/{print $2; exit}' /proc/cpuinfo)"
printf '%-14s %s\n' Threads "$(nproc)"
printf '%-14s %s\n' RAM "$(awk '/MemTotal/{printf "%.1f GB\n", $2/1048576}' /proc/meminfo)"
[ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ] &&
  printf '%-14s %s\n' Governor "$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
echo

echo "### GPU"
if command -v lspci >/dev/null 2>&1; then
  lspci | grep -Ei 'vga|3d controller' || true
fi
if command -v glxinfo >/dev/null 2>&1; then
  echo "OpenGL (BUI's GPU renderer path):"
  glxinfo -B 2>/dev/null | grep -E 'OpenGL (vendor|renderer|core profile version)' || true
fi
if command -v vulkaninfo >/dev/null 2>&1; then
  echo "Vulkan (gpui's renderer path):"
  vulkaninfo --summary 2>/dev/null | grep -E 'deviceName|driverInfo|apiVersion' | head -4 || true
else
  echo "Vulkan: installed (libvulkan), vulkaninfo not available"
fi
echo

echo "### Display"
printf '%-14s %s\n' Session "${XDG_SESSION_TYPE:-unknown}"
printf '%-14s %s\n' DISPLAY "${DISPLAY:-none}"
printf '%-14s %s\n' WAYLAND_DISPLAY "${WAYLAND_DISPLAY:-none}"
echo

echo "### Toolchain"
command -v rustc >/dev/null 2>&1 && rustc --version || echo "rustc not on PATH"
command -v cargo >/dev/null 2>&1 && cargo --version || true
