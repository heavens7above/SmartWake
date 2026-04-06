import 'dart:math';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  static const defaultApiKey = String.fromEnvironment(
    'SMARTWAKE_API_KEY',
    defaultValue: '',
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

  static SharedPreferences? _prefs;

  static Future<void> init() async {
    _prefs ??= await SharedPreferences.getInstance();
  }

  static SharedPreferences get _store {
    final prefs = _prefs;
    if (prefs == null) {
      throw StateError('StorageService.init() must be called before use.');
    }
    return prefs;
  }

  // ── Device ID ──────────────────────────────────────────────
  static String getDeviceId() {
    var id = _store.getString(_kDeviceId);
    if (id == null || id.isEmpty) {
      final rng = Random.secure();
      id = List.generate(
        16,
        (_) => rng.nextInt(256),
      ).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
      _store.setString(_kDeviceId, id);
    }
    return id;
  }

  static Future<void> setDeviceId(String id) async {
    final trimmed = id.trim();
    if (trimmed.isEmpty) {
      await resetDeviceId();
      return;
    }
    await _store.setString(_kDeviceId, trimmed);
  }

  static Future<void> resetDeviceId() async => _store.remove(_kDeviceId);

  // ── API Key ────────────────────────────────────────────────
  static String getApiKey() {
    final apiKey = _store.getString(_kApiKey)?.trim();
    return apiKey != null && apiKey.isNotEmpty ? apiKey : defaultApiKey;
  }

  static Future<void> setApiKey(String k) async {
    final trimmed = k.trim();
    if (trimmed.isEmpty) {
      await _store.remove(_kApiKey);
      return;
    }
    await _store.setString(_kApiKey, trimmed);
  }

  // ── Base URL ───────────────────────────────────────────────
  static String getBaseUrl() {
    final stored = _store.getString(_kBaseUrl)?.trim();
    final value = stored != null && stored.isNotEmpty ? stored : defaultBaseUrl;
    return value.replaceAll(RegExp(r'/$'), '');
  }

  static Future<void> setBaseUrl(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/$'), '');
    if (normalized.isEmpty) {
      await _store.remove(_kBaseUrl);
      return;
    }
    await _store.setString(_kBaseUrl, normalized);
  }

  // ── Alarm Audio Path ───────────────────────────────────────
  static String? getAlarmAudioPath() => _store.getString(_kAlarmAudioPath);

  static Future<void> setAlarmAudioPath(String path) async {
    final trimmed = path.trim();
    if (trimmed.isEmpty) {
      await _store.remove(_kAlarmAudioPath);
      return;
    }
    await _store.setString(_kAlarmAudioPath, trimmed);
  }

  // ── Alarm Time (persistent) ────────────────────────────────
  static TimeOfDay? getAlarmTime() {
    final hour = _store.getInt(_kAlarmHour);
    final minute = _store.getInt(_kAlarmMinute);
    if (hour == null || minute == null) return null;
    return TimeOfDay(hour: hour, minute: minute);
  }

  static Future<void> setAlarmTime(TimeOfDay time) async {
    await _store.setInt(_kAlarmHour, time.hour);
    await _store.setInt(_kAlarmMinute, time.minute);
  }

  static Future<void> clearAlarmTime() async {
    await _store.remove(_kAlarmHour);
    await _store.remove(_kAlarmMinute);
  }

  // ── Monitoring state ───────────────────────────────────────
  static bool getIsMonitoring() => _store.getBool(_kMonitoring) ?? false;

  static Future<void> setIsMonitoring(bool v) async =>
      _store.setBool(_kMonitoring, v);

  static bool getSetupPermissionsPrompted() =>
      _store.getBool(_kSetupPermissionsPrompted) ?? false;

  static Future<void> setSetupPermissionsPrompted(bool value) async =>
      _store.setBool(_kSetupPermissionsPrompted, value);
}
