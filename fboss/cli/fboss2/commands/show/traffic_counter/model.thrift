package "facebook.com/fboss/cli"

namespace cpp2 facebook.fboss.cli

struct ShowTrafficCounterModel {
  1: list<TrafficCounterEntry> counters;
}

// One row per counter and counter type (PACKETS or BYTES).
struct TrafficCounterEntry {
  1: string name;
  2: string type;
  // Cumulative since the agent created the counter. Absent, along with the
  // rates, when the agent exports no stat for this counter and type, i.e.
  // nothing references the counter yet.
  3: optional i64 total;
  // Per-second averages over the trailing window.
  4: optional i64 rateOneMinute;
  5: optional i64 rateTenMinutes;
  6: optional i64 rateOneHour;
}
