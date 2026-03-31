import 'dart:convert';
import 'package:http/http.dart' as http;
import 'storage_service.dart';
import '../models/models.dart';

class ApiService {
  static Future<Map<String, String>> _headers() async => {
    'Content-Type': 'application/json',
    'X-API-Key': await StorageService.getApiKey(),
  };

  static Future<String> _base() => StorageService.getBaseUrl();

  static Future<Uri> _uri(
    String path, [
    Map<String, String>? queryParameters,
  ]) async {
    final base = Uri.parse(await _base());
    return base.replace(
      path: '${base.path}${path.startsWith('/') ? path : '/$path'}',
      queryParameters: queryParameters,
    );
  }

  static Map<String, dynamic>? _decodeMap(String body) {
    final decoded = jsonDecode(body);
    return decoded is Map<String, dynamic> ? decoded : null;
  }

  // ── POST /logs/raw.log ─────────────────────────────────────
  static Future<TelemetryResponse?> postTelemetry({
    required String deviceId,
    required DateTime timestamp,
    required bool charging,
    required int batteryLevel,
    required double accelX,
    required double accelY,
    required double accelZ,
  }) async {
    try {
      final res = await http
          .post(
            await _uri('/logs/raw.log'),
            headers: await _headers(),
            body: jsonEncode({
              'device_id': deviceId,
              'timestamp': timestamp.toIso8601String(),
              'charging': charging,
              'battery_level': batteryLevel,
              'accel_x': accelX,
              'accel_y': accelY,
              'accel_z': accelZ,
              'notification_count': 0,
            }),
          )
          .timeout(const Duration(seconds: 15));
      if (res.statusCode == 200) {
        final data = _decodeMap(res.body);
        if (data != null) return TelemetryResponse.fromJson(data);
      }
    } catch (_) {}
    return null;
  }

  // ── POST /wake-time ────────────────────────────────────────
  static Future<bool> setWakeTime(String deviceId, DateTime deadline) async {
    try {
      final res = await http
          .post(
            await _uri('/wake-time'),
            headers: await _headers(),
            body: jsonEncode({
              'device_id': deviceId,
              'wake_deadline': deadline.toIso8601String(),
            }),
          )
          .timeout(const Duration(seconds: 10));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── GET /alarm-status ──────────────────────────────────────
  static Future<AlarmStatus?> getAlarmStatus(String deviceId) async {
    try {
      final res = await http
          .get(
            await _uri('/alarm-status', {'device_id': deviceId}),
            headers: await _headers(),
          )
          .timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        final data = _decodeMap(res.body);
        if (data != null) return AlarmStatus.fromJson(data);
      }
    } catch (_) {}
    return null;
  }

  // ── GET /dashboard ─────────────────────────────────────────
  static Future<DashboardData?> getDashboard(String deviceId) async {
    try {
      final res = await http
          .get(
            await _uri('/dashboard', {'device_id': deviceId}),
            headers: await _headers(),
          )
          .timeout(const Duration(seconds: 12));
      if (res.statusCode == 200) {
        final data = _decodeMap(res.body);
        if (data != null) return DashboardData.fromJson(data);
      }
    } catch (_) {}
    return null;
  }

  // ── POST /rating ───────────────────────────────────────────
  static Future<bool> submitRating(String deviceId, int rating) async {
    try {
      final res = await http
          .post(
            await _uri('/rating'),
            headers: await _headers(),
            body: jsonEncode({'device_id': deviceId, 'quality_rating': rating}),
          )
          .timeout(const Duration(seconds: 10));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── GET /health ────────────────────────────────────────────
  static Future<bool> checkHealth() async {
    try {
      final res = await http
          .get(await _uri('/health'))
          .timeout(const Duration(seconds: 8));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── POST /register ─────────────────────────────────────────
  static Future<bool> registerDevice(String deviceId) async {
    try {
      final res = await http
          .post(
            await _uri('/register'),
            headers: await _headers(),
            body: jsonEncode({'device_id': deviceId}),
          )
          .timeout(const Duration(seconds: 10));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── POST /wake-ack ─────────────────────────────────────────
  static Future<bool> ackWake(String deviceId) async {
    try {
      final res = await http
          .post(
            await _uri('/wake-ack'),
            headers: await _headers(),
            body: jsonEncode({'device_id': deviceId}),
          )
          .timeout(const Duration(seconds: 10));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
