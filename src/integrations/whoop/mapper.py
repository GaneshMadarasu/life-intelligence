"""
Maps raw Whoop API responses to the internal graph schema used by FitnessGraphBuilder.

Whoop data shapes → graph nodes:
  sleep     → SleepRecord  (extended with Whoop-specific fields)
  workout   → Workout       (extended with strain, HR zones)
  recovery  → WhoopRecovery (new node type)
  cycle     → WhoopCycle    (new node type)
"""

from __future__ import annotations

from datetime import datetime, timezone

# Whoop sport_id → human-readable workout type
SPORT_NAMES: dict[int, str] = {
    -1:  "activity",
    0:   "running",
    1:   "cycling",
    2:   "baseball",
    3:   "boxing",
    7:   "basketball",
    9:   "rowing",
    10:  "fencing",
    11:  "field_hockey",
    13:  "hiking",
    14:  "hockey",
    15:  "soccer",
    16:  "swimming",
    17:  "tennis",
    18:  "volleyball",
    21:  "golf",
    24:  "martial_arts",
    26:  "weightlifting",
    27:  "cross_training",
    28:  "yoga",
    29:  "pilates",
    32:  "elliptical",
    33:  "stairmaster",
    39:  "gymnastics",
    42:  "stretching",
    44:  "strength_training",
    45:  "walking",
    47:  "basketball",
    48:  "spinning",
    55:  "crossfit",
    56:  "obstacle_course",
    57:  "skateboarding",
    58:  "surfing",
    63:  "rock_climbing",
    71:  "cricket",
    72:  "squash",
    73:  "badminton",
    74:  "table_tennis",
    75:  "racquetball",
}


def _isodate(ts: str | None) -> str:
    """Convert ISO timestamp to YYYY-MM-DD date string."""
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        return ts[:10] if len(ts) >= 10 else ""


def _ms_to_hours(ms: int | None) -> float:
    if not ms:
        return 0.0
    return round(ms / 3_600_000, 2)


def map_sleep(record: dict) -> dict:
    """Whoop sleep record → SleepRecord dict for graph_builder."""
    score = record.get("score") or {}
    stages = score.get("stage_summary") or {}

    total_in_bed_ms    = stages.get("total_in_bed_time_milli", 0)
    total_awake_ms     = stages.get("total_awake_time_milli", 0)
    light_ms           = stages.get("total_light_sleep_time_milli", 0)
    slow_wave_ms       = stages.get("total_slow_wave_sleep_time_milli", 0)
    rem_ms             = stages.get("total_rem_sleep_time_milli", 0)

    asleep_ms          = total_in_bed_ms - total_awake_ms
    duration_hours     = _ms_to_hours(asleep_ms)

    performance        = score.get("sleep_performance_percentage", 0)
    # Map 0-100 performance → 1-10 quality scale used internally
    quality            = round(max(1, min(10, (performance or 0) / 10)), 1)

    return {
        "date":                  _isodate(record.get("start")),
        "duration_hours":        duration_hours,
        "quality":               quality,
        "deep_sleep_hours":      _ms_to_hours(slow_wave_ms),
        "rem_hours":             _ms_to_hours(rem_ms),
        "light_sleep_hours":     _ms_to_hours(light_ms),
        "time_in_bed_hours":     _ms_to_hours(total_in_bed_ms),
        "sleep_performance_pct": performance,
        "sleep_efficiency_pct":  score.get("sleep_efficiency_percentage", 0),
        "sleep_consistency_pct": score.get("sleep_consistency_percentage", 0),
        "respiratory_rate":      score.get("respiratory_rate", 0),
        "cycle_count":           stages.get("sleep_cycle_count", 0),
        "disturbances":          stages.get("disturbance_count", 0),
        "is_nap":                record.get("nap", False),
        "whoop_sleep_id":        record.get("id"),
        "source":                "whoop",
        "notes":                 f"Whoop sleep {record.get('score_state', 'SCORED')}",
    }


def map_workout(record: dict) -> dict:
    """Whoop workout record → Workout dict for graph_builder."""
    score     = record.get("score") or {}
    zones     = score.get("zone_duration") or {}
    sport_id  = record.get("sport_id", -1)
    sport     = SPORT_NAMES.get(sport_id, f"sport_{sport_id}")

    start     = record.get("start", "")
    end       = record.get("end", "")

    # Duration in minutes
    if start and end:
        try:
            s = datetime.fromisoformat(start.replace("Z", "+00:00"))
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
            duration_mins = int((e - s).total_seconds() / 60)
        except Exception:
            duration_mins = 0
    else:
        duration_mins = 0

    # Whoop kilojoules → kcal (1 kJ ≈ 0.239 kcal)
    kj            = score.get("kilojoule", 0) or 0
    calories      = round(kj * 0.239)

    strain        = score.get("strain", 0) or 0
    # Map strain (0-21 Whoop scale) → intensity label
    if strain >= 18:
        intensity = "high"
    elif strain >= 12:
        intensity = "moderate"
    elif strain >= 6:
        intensity = "low"
    else:
        intensity = "minimal"

    def _ms_to_min(ms): return round((ms or 0) / 60_000, 1)

    return {
        "date":              _isodate(start),
        "type":              sport,
        "duration_mins":     duration_mins,
        "calories_burned":   calories,
        "intensity":         intensity,
        "strain_score":      strain,
        "avg_heart_rate":    score.get("average_heart_rate", 0),
        "max_heart_rate":    score.get("max_heart_rate", 0),
        "distance_meters":   score.get("distance_meter", 0),
        "altitude_gain_m":   score.get("altitude_gain_meter", 0),
        "hr_zone_1_mins":    _ms_to_min(zones.get("zone_one_milli")),
        "hr_zone_2_mins":    _ms_to_min(zones.get("zone_two_milli")),
        "hr_zone_3_mins":    _ms_to_min(zones.get("zone_three_milli")),
        "hr_zone_4_mins":    _ms_to_min(zones.get("zone_four_milli")),
        "hr_zone_5_mins":    _ms_to_min(zones.get("zone_five_milli")),
        "whoop_workout_id":  record.get("id"),
        "source":            "whoop",
        "notes":             f"Whoop {sport} strain={strain:.1f}",
    }


def map_recovery(record: dict) -> dict:
    """Whoop recovery record → WhoopRecovery dict."""
    score = record.get("score") or {}
    return {
        "date":             _isodate(record.get("created_at")),
        "recovery_score":   score.get("recovery_score", 0),
        "hrv_rmssd":        score.get("hrv_rmssd_milli", 0),
        "resting_hr":       score.get("resting_heart_rate", 0),
        "spo2_pct":         score.get("spo2_percentage", 0),
        "skin_temp_celsius":score.get("skin_temp_celsius", 0),
        "whoop_cycle_id":   record.get("cycle_id"),
        "whoop_sleep_id":   record.get("sleep_id"),
        "score_state":      record.get("score_state", "SCORED"),
    }


def map_cycle(record: dict) -> dict:
    """Whoop daily cycle → WhoopCycle dict."""
    score = record.get("score") or {}
    kj    = score.get("kilojoule", 0) or 0
    return {
        "date":              _isodate(record.get("start")),
        "strain":            score.get("strain", 0),
        "kilojoule":         kj,
        "calories":          round(kj * 0.239),
        "avg_heart_rate":    score.get("average_heart_rate", 0),
        "max_heart_rate":    score.get("max_heart_rate", 0),
        "score_state":       record.get("score_state", "SCORED"),
        "whoop_cycle_id":    record.get("id"),
    }
