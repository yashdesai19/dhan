#!/usr/bin/env bash
# Records the 4 raw DHAN portfolio clips on the Android emulator (1080x2400, AVD "medium_phone").
#
# Prerequisites (see README section at the bottom of this file):
#   1. mock/db.ts temporarily imports '../portfolio-clips/demo-seed' instead of './seed'.
#   2. Emulator running:  emulator -avd medium_phone -no-snapshot-save -no-audio -gpu host
#   3. Metro on mock data: EXPO_PUBLIC_DHAN_API_URL= npx expo start --port 8082
#   4. In Expo Go: signed in once as demo@example.com and the dev menu's "Tools button" switched off.
#
# Usage: bash portfolio-clips/record.sh [1|2|3|4|all]   -> writes portfolio-clips/raw/clip-N.mp4
set -euo pipefail
export MSYS_NO_PATHCONV=1

ADB="${ADB:-$LOCALAPPDATA/Android/Sdk/platform-tools/adb.exe}"
URL="${EXPO_URL:-exp://10.0.2.2:8082}"
OUT="$(cd "$(dirname "$0")" && pwd)/raw"
mkdir -p "$OUT"
command -v cygpath >/dev/null && OUT="$(cygpath -m "$OUT")" # Windows adb needs D:/ paths

adb() { "$ADB" "$@"; }
wait_s() { sleep "$1"; }
tap() { adb shell input tap "$1" "$2"; }
# Slow drag with no fling: x y1 y2 duration_ms
drag() { adb shell input swipe "$1" "$2" "$1" "$3" "$4"; }
type_slow() { # ~80 ms per character
  local s="$1" i c
  for ((i = 0; i < ${#s}; i++)); do
    c="${s:i:1}"; [[ "$c" == " " ]] && c="%s"
    adb shell input text "$c"
  done
}

demo_mode_on() {
  adb shell settings put global sysui_demo_allowed 1
  local b=(shell am broadcast -a com.android.systemui.demo -e command)
  adb "${b[@]}" enter >/dev/null
  adb "${b[@]}" clock -e hhmm 0941 >/dev/null
  adb "${b[@]}" battery -e level 100 -e plugged false >/dev/null
  adb "${b[@]}" network -e wifi hide >/dev/null
  adb "${b[@]}" network -e mobile show -e datatype lte -e level 4 -e fully true >/dev/null
  adb "${b[@]}" notifications -e visible false >/dev/null
  # Light theme: the emulator is left in light mode. Don't toggle `cmd uimode` here, because
  # the configuration change closes the running Expo Go experience.
}

# Puts the already-loaded app back on the top of a tab without restarting it. A cold restart
# brings back the splash, the app lock and loading skeletons, so the app stays open for all clips;
# clip 2 (the only one that adds data) runs last. Re-launch Expo Go to reset the mock data.
reset_app() {
  if ! adb shell dumpsys activity activities | grep -m1 topResumedActivity | grep -q ExperienceActivity; then
    echo "DHAN is not in the foreground in Expo Go; open it first (adb shell am start -d $URL)." >&2
    exit 1
  fi
  tap $TAB_HOME; wait_s 0.8; tap $TAB_HOME; wait_s 0.5
  drag 540 700 2000 150; wait_s 0.4; drag 540 700 2000 150; wait_s 1.2   # back to the top
}

rec_start() { adb shell "screenrecord --bit-rate 16000000 /sdcard/clip-$1.mp4" & REC_PID=$!; wait_s 1; }
rec_stop() {
  adb shell pkill -INT screenrecord || true
  wait "$REC_PID" 2>/dev/null || true
  wait_s 1.5
  adb pull "/sdcard/clip-$1.mp4" "$OUT/clip-$1.mp4" >/dev/null
  adb shell rm "/sdcard/clip-$1.mp4"
  echo "saved $OUT/clip-$1.mp4"
}

# Tab bar and screen coordinates (1080x2400).
TAB_HOME="110 2240"; TAB_ACTIVITY="335 2240"; TAB_ADD="540 2215"; TAB_MORE="945 2240"

clip1() { # Home overview with a gentle scroll down and back
  reset_app; tap $TAB_HOME; wait_s 1
  rec_start 1
  wait_s 1.5
  drag 540 1800 900 2200; wait_s 1.4
  drag 540 1700 1000 1600; wait_s 1.2
  drag 540 700 2300 2600; wait_s 1.5
  rec_stop 1
}

clip2() { # Add a ₹450 "Coffee House" expense and see it on Home
  reset_app; tap $TAB_HOME; wait_s 1
  rec_start 2
  wait_s 1
  tap 166 991; wait_s 2                        # Home's "Expense" quick action opens the entry screen
  tap 209 1754; wait_s 0.25; tap 540 1754; wait_s 0.25; tap 540 2081; wait_s 0.8   # 4 5 0 on the in-app keypad
  tap 120 1423; wait_s 1.2                     # + Note, wait for the keyboard
  type_slow "Coffee House"; wait_s 0.5
  adb shell input keyevent 111; wait_s 0.6     # dismiss keyboard
  tap 135 863; wait_s 0.8                      # Food chip
  tap 540 2263; wait_s 1                       # Save
  tap 110 139; wait_s 1                        # close entry, back on Home
  drag 540 1900 800 1600; wait_s 2.2           # scroll to "Recent"
  rec_stop 2
}

clip3() { # Reports: income vs spending bars grow in, then category bars
  reset_app; tap $TAB_MORE; wait_s 1.5
  rec_start 3
  wait_s 1
  tap 540 1627; wait_s 2.4                     # "Reports and net worth"
  drag 540 1900 1050 1800; wait_s 2.2
  rec_stop 3
  adb shell input keyevent 4; wait_s 1          # leave Reports (off camera)
}

clip4() { # Activity history: scroll, open one transaction, go back
  reset_app; tap $TAB_ACTIVITY; wait_s 1.5
  rec_start 4
  wait_s 1.2
  drag 540 1900 1000 1800; wait_s 1
  drag 540 1000 1900 1500; wait_s 0.8
  tap 540 ${DETAIL_ROW_Y:-720}; wait_s 2.2      # open a transaction's detail
  adb shell input keyevent 4; wait_s 1.5
  rec_stop 4
}

demo_mode_on
case "${1:-all}" in
  1) clip1 ;; 2) clip2 ;; 3) clip3 ;; 4) clip4 ;;
  all) clip1; clip3; clip4; clip2 ;;
esac

# Afterwards, turn demo mode off:
#   adb shell am broadcast -a com.android.systemui.demo -e command exit
#   adb shell settings put global sysui_demo_allowed 0
