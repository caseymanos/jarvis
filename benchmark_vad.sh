#!/bin/bash

# =====================================================
# Android VAD Benchmarking Script
# Author: Casey Manos
# =====================================================

PKG="com.frontieraudio.heartbeat"
DURATION=30                      # seconds
TRACE_FILE="vad_trace.perfetto-trace"

read -r -d '' PERFETTO_CONFIG <<'EOF'
buffers {
  size_kb: 32768
  fill_policy: RING_BUFFER
}
duration_ms: 30000
data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "sched/sched_process_exit"
      atrace_categories: "app"
      atrace_categories: "dalvik"
      atrace_categories: "audio"
      atrace_apps: "com.frontieraudio.heartbeat"
    }
  }
}
data_sources { config { name: "process_stats" } }
data_sources { 
  config { 
    name: "track_event"
    track_event_config {
      enabled_categories: "*"
    }
  } 
}
data_sources { config { name: "android.power" } }
data_sources { config { name: "android.processes" } }
data_sources { config { name: "android.packages_list" } }
EOF

# --- 2. Get target PID -------------------------------------------------------
PID=$(adb shell pidof $PKG | tr -d '\r')
if [ -z "$PID" ]; then
  echo "❌ Could not find PID for $PKG. Make sure app is running."
  exit 1
fi
echo "✅ PID = $PID"

echo "🧼 Clearing logcat buffer..."
adb logcat -c

# --- 3. Run atrace (simpler, more reliable for app tracing) -----------------
echo "📈 Starting atrace for $DURATION s..."
adb shell "atrace --async_start -b 32768 -t $DURATION app dalvik audio sched freq idle am wm gfx view binder_driver hal res dalvik"
echo "⏱️  Recording for $DURATION seconds..."
sleep $DURATION
adb shell "atrace --async_stop" > "$TRACE_FILE"
if [ -s "$TRACE_FILE" ]; then
  echo "✅ Trace saved to $(pwd)/$TRACE_FILE ($(du -h "$TRACE_FILE" | cut -f1))"
else
  echo "❌ Trace capture failed or empty."
  exit 1
fi

# --- 5. Run simpleperf sample ------------------------------------------------
echo "🔬 Running simpleperf sampling for 10s..."
if adb shell simpleperf record -p $PID --duration 10 --call-graph fp -o /data/local/tmp/perf.data; then
  adb shell simpleperf report -i /data/local/tmp/perf.data > simpleperf_report.txt
  adb pull /data/local/tmp/perf.data . 2>/dev/null || true
  echo "✅ simpleperf results saved."
  adb shell rm /data/local/tmp/perf.data >/dev/null 2>&1
else
  echo "⚠️ simpleperf sampling failed (requires profiling permission on production builds). Skipping."
fi

# --- 6. Optional battery stats snapshot -------------------------------------
echo "🔋 Capturing batterystats..."
adb shell dumpsys batterystats > batterystats_vad.txt

# --- 7. Capture Stage 1 segment summary --------------------------------------
echo "🗒️  Capturing Stage 1 segment events..."
adb logcat -d > logcat_stage1.txt
grep "Stage1 segment ready" logcat_stage1.txt > stage1_segments.log || true

# --- 7. Cleanup --------------------------------------------------------------
echo "🧹 Cleanup done."

TRACE_PATH="$(pwd)/$TRACE_FILE"
if [ -f simpleperf_report.txt ]; then
  SIMPLEPERF_PATH="$(pwd)/simpleperf_report.txt"
else
  SIMPLEPERF_PATH="(not generated)"
fi

if [ -f batterystats_vad.txt ]; then
  BATTERY_PATH="$(pwd)/batterystats_vad.txt"
else
  BATTERY_PATH="(not generated)"
fi

if [ -f stage1_segments.log ] && [ -s stage1_segments.log ]; then
  SEGMENT_PATH="$(pwd)/stage1_segments.log"
else
  SEGMENT_PATH="(no segments captured)"
fi

echo "----------------------------------------------------------"
echo "Open Perfetto trace at: https://ui.perfetto.dev"
echo "File: $TRACE_PATH"
echo "simpleperf summary: $SIMPLEPERF_PATH"
echo "Battery stats: $BATTERY_PATH"
echo "Stage 1 segments: $SEGMENT_PATH"
echo "----------------------------------------------------------"

