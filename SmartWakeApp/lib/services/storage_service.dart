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
  static const _kSetupPermissionsPrompted = 'setup_permissions_prompted';

  static late final SharedPreferences _prefs;

  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  // ── Device ID ──────────────────────────────────────────────
  static Future<String> getDeviceId() async {
    var id = _prefs.getString(_kDeviceId);
    if (id == null || id.isEmpty) {
      final rng = Random.secure();
      id = List.generate(
        16,
        (_) => rng.nextInt(256),
      ).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      await _prefs.setString(_kDeviceId, id);
    }
    return id;
  }

  static Future<void> setDeviceId(String id) async {
    final trimmed = id.trim();
    if (trimmed.isEmpty) {
      await resetDeviceId();
      return;
    }
    await _prefs.setString(_kDeviceId, trimmed);
  }

  static Future<void> resetDeviceId() async => _prefs.remove(_kDeviceId);

  // ── API Key ────────────────────────────────────────────────
  static Future<String> getApiKey() async {
    final apiKey = _prefs.getString(_kApiKey)?.trim();
    return apiKey != null && apiKey.isNotEmpty ? apiKey : defaultApiKey;
  }

  static Future<void> setApiKey(String k) async {
    final trimmed = k.trim();
    if (trimmed.isEmpty) {
      await _prefs.remove(_kApiKey);
      return;
    }
    await _prefs.setString(_kApiKey, trimmed);
  }

  // ── Base URL ───────────────────────────────────────────────
  static Future<String> getBaseUrl() async {
    final stored = _prefs.getString(_kBaseUrl)?.trim();
    final value = stored != null && stored.isNotEmpty ? stored : defaultBaseUrl;
    return value.replaceAll(RegExp(r'/$'), '');
  }

  static Future<void> setBaseUrl(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/$'), '');
    if (normalized.isEmpty) {
      await _prefs.remove(_kBaseUrl);
      return;
    }
    await _prefs.setString(_kBaseUrl, normalized);
  }

  // ── Alarm Audio Path ───────────────────────────────────────
  static Future<String?> getAlarmAudioPath() async =>
      _prefs.getString(_kAlarmAudioPath);

  static Future<void> setAlarmAudioPath(String path) async {
    final trimmed = path.trim();
    if (trimmed.isEmpty) {
      await _prefs.remove(_kAlarmAudioPath);
      return;
    }
    await _prefs.setString(_kAlarmAudioPath, trimmed);
  }

  // ── Alarm Time (persistent) ────────────────────────────────
  static Future<TimeOfDay?> getAlarmTime() async {
    final hour = _prefs.getInt(_kAlarmHour);
    final minute = _prefs.getInt(_kAlarmMinute);
    if (hour == null || minute == null) return null;
    return TimeOfDay(hour: hour, minute: minute);
  }

  static Future<void> setAlarmTime(TimeOfDay time) async {
    await _prefs.setInt(_kAlarmHour, time.hour);
    await _prefs.setInt(_kAlarmMinute, time.minute);
  }

  static Future<void> clearAlarmTime() async {
    await _prefs.remove(_kAlarmHour);
    await _prefs.remove(_kAlarmMinute);
  }

  // ── Monitoring state ───────────────────────────────────────
  static Future<bool> getIsMonitoring() async =>
      _prefs.getBool(_kMonitoring) ?? false;

  static Future<void> setIsMonitoring(bool v) async =>
      _prefs.setBool(_kMonitoring, v);

  static Future<bool> getSetupPermissionsPrompted() async =>
      _prefs.getBool(_kSetupPermissionsPrompted) ?? false;

  static Future<void> setSetupPermissionsPrompted(bool value) async =>
      _prefs.setBool(_kSetupPermissionsPrompted, value);
}
