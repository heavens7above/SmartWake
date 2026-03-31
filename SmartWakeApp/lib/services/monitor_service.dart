import 'dart:async';
import 'dart:convert';
import 'dart:ui';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'package:battery_plus/battery_plus.dart';
import 'package:http/http.dart' as http;
import 'storage_service.dart';

// ── Foreground service entry point ──────────────────────────
// Must be top-level so the OS can locate it.
@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(SleepMonitorHandler());
}

// ── Task Handler (runs in service isolate) ──────────────────
class SleepMonitorHandler extends TaskHandler {
  double _x = 0, _y = 0, _z = 0;
  StreamSubscription<UserAccelerometerEvent>? _accelSub;
  final _battery = Battery();
  String? _lastAlarmDate; // prevent double-firing per day

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter starter) async {
    DartPluginRegistrant.ensureInitialized();
    _accelSub =
        userAccelerometerEventStream(
          samplingPeriod: SensorInterval.normalInterval,
        ).listen((e) {
          _x = e.x;
          _y = e.y;
          _z = e.z;
        });
  }

  @override
  void onRepeatEvent(DateTime timestamp) async {
    await _postTelemetry(timestamp);
    await _checkAlarm();
  }

  @override
  Future<void> onDestroy(DateTime timestamp) async {
    await _accelSub?.cancel();
  }

  // ── telemetry upload ──────────────────────────────────────
  Future<void> _postTelemetry(DateTime now) async {
    try {
      final deviceId = await StorageService.getDeviceId();
      final apiKey = await StorageService.getApiKey();
      final baseUrl = await StorageService.getBaseUrl();

      int level = 50;
      bool charging = false;
      try {
        level = await _battery.batteryLevel;
        final s = await _battery.batteryState;
        charging = s == BatteryState.charging || s == BatteryState.full;
      } catch (_) {}

      final res = await http
          .post(
            Uri.parse('$baseUrl/logs/raw.log'),
            headers: {'Content-Type': 'application/json', 'X-API-Key': apiKey},
            body: jsonEncode({
              'device_id': deviceId,
              'timestamp': now.toIso8601String(),
              'charging': charging,
              'battery_level': level,
              'accel_x': _x,
              'accel_y': _y,
              'accel_z': _z,
              'notification_count': 0,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final state = data['state'] ?? 'TRACKING';
        final sleepProb = (data['sleep_prob'] ?? 0.0).toDouble();

        // Notify main isolate
        FlutterForegroundTask.sendDataToMain({
          'type': 'telemetry',
          'state': state,
          'sleep_prob': sleepProb,
          'onset_time': data['onset_time'],
          'consecutive': data['consecutive_above_threshold'] ?? 0,
          'battery': level,
          'charging': charging,
          'accel_x': _x,
          'accel_y': _y,
          'accel_z': _z,
        });

        final label = state == 'CONFIRMED'
            ? '💤 Sleep confirmed'
            : '👁 Tracking — ${(sleepProb * 100).toStringAsFixed(0)}% sleep prob';
        await FlutterForegroundTask.updateService(
          notificationTitle: 'SmartWake Active',
          notificationText: label,
        );
      } else {
        FlutterForegroundTask.sendDataToMain({
          'type': 'telemetry_error',
          'status': res.statusCode,
          'body': res.body,
        });
      }
    } catch (e) {
      FlutterForegroundTask.sendDataToMain({
        'type': 'telemetry_error',
        'error': e.toString(),
      });
    }
  }

  // ── alarm checker ─────────────────────────────────────────
  Future<void> _checkAlarm() async {
    try {
      final deviceId = await StorageService.getDeviceId();
      final apiKey = await StorageService.getApiKey();
      final baseUrl = await StorageService.getBaseUrl();

      final res = await http
          .get(
            Uri.parse('$baseUrl/alarm-status?device_id=$deviceId'),
            headers: {'X-API-Key': apiKey},
          )
          .timeout(const Duration(seconds: 10));

      if (res.statusCode != 200) return;
      final data = jsonDecode(res.body) as Map<String, dynamic>;

      // Server tells us definitively whether to fire
      if (data['should_fire'] == true && _lastAlarmDate != data['alarm_time']) {
        _lastAlarmDate = data['alarm_time'] as String?;
        FlutterForegroundTask.sendDataToMain({
          'type': 'alarm',
          'alarm_time': data['alarm_time'],
        });
        await FlutterForegroundTask.updateService(
          notificationTitle: '⏰ Wake Up — SmartWake',
          notificationText: 'Optimal sleep cycle complete. Rise and shine!',
        );
      }
    } catch (_) {}
  }
}

// ── Static helper used from UI ──────────────────────────────
class MonitorService {
  static void init() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'smartwake_monitor',
        channelName: 'SmartWake Monitor',
        channelDescription: 'Active sleep telemetry service',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: false,
      ),
      foregroundTaskOptions: ForegroundTaskOptions(
        eventAction: ForegroundTaskEventAction.repeat(5 * 60 * 1000), // 5 min
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  static Future<bool> get isRunning => FlutterForegroundTask.isRunningService;

  static Future<ServiceRequestResult> start() async {
    if (await FlutterForegroundTask.isRunningService) {
      return FlutterForegroundTask.restartService();
    }
    return FlutterForegroundTask.startService(
      serviceId: 256,
      notificationTitle: 'SmartWake Active',
      notificationText: 'Starting sleep monitoring...',
      callback: startCallback,
    );
  }

  static Future<ServiceRequestResult> stop() =>
      FlutterForegroundTask.stopService();
}
