double _asDouble(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? 0.0;
  return 0.0;
}

int _asInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

Map<String, dynamic>? _asMap(Object? value) =>
    value is Map ? value.map((key, val) => MapEntry('$key', val)) : null;

class TelemetryResponse {
  final String state;
  final double sleepProb;
  final String? onsetTime;
  final int consecutive;

  TelemetryResponse({
    required this.state,
    required this.sleepProb,
    this.onsetTime,
    required this.consecutive,
  });

  factory TelemetryResponse.fromJson(Map<String, dynamic> j) =>
      TelemetryResponse(
        state: j['state'] ?? 'TRACKING',
        sleepProb: _asDouble(j['sleep_prob']),
        onsetTime: j['onset_time'],
        consecutive: _asInt(j['consecutive_above_threshold']),
      );
}

class AlarmStatus {
  final bool scheduled;
  final String? alarmTime;

  AlarmStatus({required this.scheduled, this.alarmTime});

  factory AlarmStatus.fromJson(Map<String, dynamic> j) => AlarmStatus(
        scheduled: j['alarm_scheduled'] == true,
        alarmTime: j['alarm_time'],
      );

  DateTime? get alarmDateTime =>
      alarmTime != null ? DateTime.tryParse(alarmTime!) : null;
}

class SleepSession {
  final int id;
  final String? onsetTime;
  final String? wakeDeadline;
  final String? alarmTime;
  final bool alarmFired;
  final int? qualityRating;
  final String createdAt;

  SleepSession({
    required this.id,
    this.onsetTime,
    this.wakeDeadline,
    this.alarmTime,
    required this.alarmFired,
    this.qualityRating,
    required this.createdAt,
  });

  factory SleepSession.fromJson(Map<String, dynamic> j) => SleepSession(
        id: _asInt(j['id']),
        onsetTime: j['onset_time'],
        wakeDeadline: j['wake_deadline'],
        alarmTime: j['alarm_time'],
        alarmFired: j['alarm_fired'] == 1 || j['alarm_fired'] == true,
        qualityRating:
            j['quality_rating'] != null ? _asInt(j['quality_rating']) : null,
        createdAt: j['created_at'] ?? '',
      );
}

class LogEntry {
  final String timestamp;
  final double? sleepProb;
  final double accelMagnitude;
  final bool charging;

  LogEntry({
    required this.timestamp,
    this.sleepProb,
    required this.accelMagnitude,
    required this.charging,
  });

  factory LogEntry.fromJson(Map<String, dynamic> j) => LogEntry(
        timestamp: j['timestamp'] ?? '',
        sleepProb: j['sleep_prob'] != null ? _asDouble(j['sleep_prob']) : null,
        accelMagnitude: _asDouble(j['accel_magnitude']),
        charging: j['charging'] == 1 || j['charging'] == true,
      );
}

class DashboardData {
  final String deviceId;
  final SleepSession? recentSession;
  final List<LogEntry> logs;

  DashboardData(
      {required this.deviceId, this.recentSession, required this.logs});

  factory DashboardData.fromJson(Map<String, dynamic> j) {
    final recentSession = _asMap(j['recent_session']);
    return DashboardData(
      deviceId: j['device_id'] ?? '',
      recentSession:
          recentSession != null ? SleepSession.fromJson(recentSession) : null,
      logs: (j['logs'] as List<dynamic>? ?? [])
          .map(_asMap)
          .whereType<Map<String, dynamic>>()
          .map(LogEntry.fromJson)
          .toList(),
    );
  }
}
