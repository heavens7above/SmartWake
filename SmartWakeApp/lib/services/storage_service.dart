import 'dart:math';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const defaultApiKey = String.fromEnvironment(
    'SMARTWAKE_API_KEY',
    defaultValue: 'sk_live_smartwake_93f8e21a',
  );
  static const defaultBaseUrl = String.fromEnvironment(
    'SMARTWAKE_BASE_URL',
    defaultValue: 'https://smartwake.up.railway.app',
  );
  static const _kDeviceId = 'device_id';
  static const _kApiKey = 'api_key';
  static const _kBaseUrl = 'base_url';
  static const _kMonitoring = 'is_monitoring';
  static const _kAlarmAudioPath = 'alarm_audio_path';
  static const _kAlarmHour = 'alarm_hour';
  static const _kAlarmMinute = 'alarm_minute';

  static Future<SharedPreferences> get _p => SharedPreferences.getInstance();

  // ── Device ID ──────────────────────────────────────────────
  static Future<String> getDeviceId() async {
    final p = await _p;
    var id = p.getString(_kDeviceId);
    if (id == null || id.isEmpty) {
      final rng = Random.secure();
      id = List.generate(
        16,
        (_) => rng.nextInt(256),
      ).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      await p.setString(_kDeviceId, id);
    }
    return id;
  }

  static Future<void> setDeviceId(String id) async {
    final trimmed = id.trim();
    if (trimmed.isEmpty) {
      await resetDeviceId();
      return;
    }
    await (await _p).setString(_kDeviceId, trimmed);
  }

  static Future<void> resetDeviceId() async => (await _p).remove(_kDeviceId);

  // ── API Key ────────────────────────────────────────────────
  static Future<String> getApiKey() async {
    final apiKey = (await _p).getString(_kApiKey)?.trim();
    return apiKey != null && apiKey.isNotEmpty ? apiKey : defaultApiKey;
  }

  static Future<void> setApiKey(String k) async {
    final trimmed = k.trim();
    if (trimmed.isEmpty) {
      await (await _p).remove(_kApiKey);
      return;
    }
    await (await _p).setString(_kApiKey, trimmed);
  }

  // ── Base URL ───────────────────────────────────────────────
  static Future<String> getBaseUrl() async {
    final stored = (await _p).getString(_kBaseUrl)?.trim();
    final value = stored != null && stored.isNotEmpty ? stored : defaultBaseUrl;
    return value.replaceAll(RegExp(r'/$'), '');
  }

  static Future<void> setBaseUrl(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/$'), '');
    if (normalized.isEmpty) {
      await (await _p).remove(_kBaseUrl);
      return;
    }
    await (await _p).setString(_kBaseUrl, normalized);
  }

  // ── Alarm Audio Path ───────────────────────────────────────
  static Future<String?> getAlarmAudioPath() async =>
      (await _p).getString(_kAlarmAudioPath);

  static Future<void> setAlarmAudioPath(String path) async {
    final trimmed = path.trim();
    if (trimmed.isEmpty) {
      await (await _p).remove(_kAlarmAudioPath);
      return;
    }
    await (await _p).setString(_kAlarmAudioPath, trimmed);
  }

  // ── Alarm Time (persistent) ────────────────────────────────
  static Future<TimeOfDay?> getAlarmTime() async {
    final p = await _p;
    final hour = p.getInt(_kAlarmHour);
    final minute = p.getInt(_kAlarmMinute);
    if (hour == null || minute == null) return null;
    return TimeOfDay(hour: hour, minute: minute);
  }

  static Future<void> setAlarmTime(TimeOfDay time) async {
    final p = await _p;
    await p.setInt(_kAlarmHour, time.hour);
    await p.setInt(_kAlarmMinute, time.minute);
  }

  static Future<void> clearAlarmTime() async {
    final p = await _p;
    await p.remove(_kAlarmHour);
    await p.remove(_kAlarmMinute);
  }

  // ── Monitoring state ───────────────────────────────────────
  static Future<bool> getIsMonitoring() async =>
      (await _p).getBool(_kMonitoring) ?? false;

  static Future<void> setIsMonitoring(bool v) async =>
      (await _p).setBool(_kMonitoring, v);
}
