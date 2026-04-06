import 'dart:io';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:path_provider/path_provider.dart';
import '../theme/app_theme.dart';
import '../widgets/glow_card.dart';
import '../widgets/star_field.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../models/models.dart';

class AlarmScreen extends StatefulWidget {
  const AlarmScreen({super.key});

  @override
  State<AlarmScreen> createState() => _AlarmScreenState();
}

class _AlarmScreenState extends State<AlarmScreen> {
  TimeOfDay? _selectedTime;
  AlarmStatus? _alarmStatus;
  bool _loading = false;
  bool _loadFailed = false;
  bool _saving = false;
  String? _deviceId;
  String? _alarmAudioPath;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    _deviceId = StorageService.getDeviceId();
    _alarmAudioPath = StorageService.getAlarmAudioPath();

    // Restore persisted alarm time
    final savedTime = StorageService.getAlarmTime();
    if (savedTime != null && mounted) {
      setState(() => _selectedTime = savedTime);
    }

    _refreshAlarm();
  }

  Future<void> _refreshAlarm() async {
    if (_deviceId == null) return;
    setState(() => _loading = true);
    final status = await ApiService.getAlarmStatus(_deviceId!);
    if (mounted) {
      setState(() {
        _alarmStatus = status;
        _loadFailed = status == null;
        _loading = false;
      });
    }
  }

  Future<void> _pickTime() async {
    final now = TimeOfDay.now();
    final pick = await showTimePicker(
      context: context,
      initialTime:
          _selectedTime ?? TimeOfDay(hour: (now.hour + 8) % 24, minute: 0),
      builder: (ctx, child) => Theme(
        data: Theme.of(ctx).copyWith(
          colorScheme: const ColorScheme.dark(
            primary: AppTheme.primary,
            surface: AppTheme.surface,
          ),
        ),
        child: child!,
      ),
    );
    if (pick != null) setState(() => _selectedTime = pick);
  }

  Future<void> _setAlarm() async {
    if (_selectedTime == null || _deviceId == null) return;
    setState(() => _saving = true);

    final now = DateTime.now();
    var deadline = DateTime(
      now.year,
      now.month,
      now.day,
      _selectedTime!.hour,
      _selectedTime!.minute,
    );
    if (!deadline.isAfter(now)) {
      deadline = deadline.add(const Duration(days: 1));
    }

    final ok = await ApiService.setWakeTime(_deviceId!, deadline);

    if (ok) {
      // Persist alarm time locally so it survives app restarts
      await StorageService.setAlarmTime(_selectedTime!);
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ok
                ? '✅ Wake time set for ${_selectedTime!.format(context)}'
                : '❌ Failed to set wake time',
          ),
          backgroundColor: ok ? AppTheme.teal : AppTheme.pink,
        ),
      );
    }
    if (ok) await _refreshAlarm();
    if (mounted) setState(() => _saving = false);
  }

  Future<void> _pickAudioFile() async {
    if (await Permission.audio.request().isGranted ||
        await Permission.storage.request().isGranted) {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.audio,
      );
      if (result != null && result.files.single.path != null) {
        final sourcePath = result.files.single.path!;
        final fileName = result.files.single.name;

        // Copy file to app's internal storage for reliable access
        final appDir = await getApplicationDocumentsDirectory();
        final alarmDir = Directory('${appDir.path}/alarm_audio');
        if (!await alarmDir.exists()) {
          await alarmDir.create(recursive: true);
        }
        final destPath = '${alarmDir.path}/$fileName';
        await File(sourcePath).copy(destPath);

        await StorageService.setAlarmAudioPath(destPath);
        setState(() => _alarmAudioPath = destPath);
      }
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Storage permission required for custom alarms')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final fmt = DateFormat('HH:mm • dd MMM');
    return StarField(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              const Text(
                'WAKE ALARM',
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 2,
                ),
              ),
              const Text(
                'Set your target wake time',
                style: TextStyle(color: AppTheme.textSecond, fontSize: 13),
              ),
              const SizedBox(height: 28),

              // Time picker card
              GlowCard(
                glowColor: AppTheme.cyan,
                child: Column(
                  children: [
                    GestureDetector(
                      onTap: _pickTime,
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(vertical: 32),
                        child: Column(
                          children: [
                            Text(
                              _selectedTime != null
                                  ? _selectedTime!.format(context)
                                  : '-- : --',
                              style: TextStyle(
                                fontSize: 56,
                                fontWeight: FontWeight.w800,
                                color: _selectedTime != null
                                    ? AppTheme.cyan
                                    : AppTheme.border,
                                letterSpacing: 2,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 4,
                              ),
                              decoration: BoxDecoration(
                                color: AppTheme.primary.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(20),
                              ),
                              child: const Text(
                                'TAP TO CHANGE',
                                style: TextStyle(
                                  color: AppTheme.primary,
                                  fontSize: 10,
                                  letterSpacing: 1.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed:
                            _selectedTime == null || _saving ? null : _setAlarm,
                        icon: _saving
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : const Icon(Icons.alarm_add),
                        label: Text(_saving ? 'SAVING...' : 'SET WAKE TIME'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.cyan,
                          shadowColor: AppTheme.cyan.withValues(alpha: 0.3),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // Current alarm status
              GlowCard(
                glowColor: _alarmStatus?.scheduled == true
                    ? AppTheme.teal
                    : AppTheme.border,
                padding: const EdgeInsets.all(16),
                child: _loading
                    ? const Center(
                        child: CircularProgressIndicator(
                          color: AppTheme.primary,
                          strokeWidth: 2,
                        ),
                      )
                    : _loadFailed
                        ? const Text(
                            'Could not load alarm status. Check server connectivity and try again.',
                            style: TextStyle(
                              color: AppTheme.textSecond,
                              fontSize: 13,
                            ),
                          )
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    _alarmStatus?.scheduled == true
                                        ? Icons.alarm_on
                                        : Icons.alarm_off,
                                    color: _alarmStatus?.scheduled == true
                                        ? AppTheme.teal
                                        : AppTheme.textSecond,
                                  ),
                                  const SizedBox(width: 10),
                                  const Text(
                                    'SCHEDULED ALARM',
                                    style: TextStyle(
                                      color: AppTheme.textSecond,
                                      fontSize: 11,
                                      letterSpacing: 1.5,
                                    ),
                                  ),
                                  const Spacer(),
                                  GestureDetector(
                                    onTap: _refreshAlarm,
                                    child: const Icon(
                                      Icons.refresh,
                                      color: AppTheme.textSecond,
                                      size: 18,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 12),
                              if (_alarmStatus?.scheduled == true &&
                                  _alarmStatus?.alarmDateTime != null) ...[
                                Text(
                                  fmt.format(_alarmStatus!.alarmDateTime!),
                                  style: const TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 24,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                const Text(
                                  'Optimised to nearest 90-min sleep cycle',
                                  style: TextStyle(
                                    color: AppTheme.textSecond,
                                    fontSize: 12,
                                  ),
                                ),
                              ] else
                                const Text(
                                  'No alarm scheduled yet',
                                  style: TextStyle(color: AppTheme.textSecond),
                                ),
                            ],
                          ),
              ),

              const SizedBox(height: 16),

              // Custom Audio Selection Card
              GlowCard(
                glowColor:
                    _alarmAudioPath != null ? AppTheme.pink : AppTheme.border,
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Icon(
                      Icons.music_note,
                      color: _alarmAudioPath != null
                          ? AppTheme.pink
                          : AppTheme.textSecond,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'ALARM SOUND',
                            style: TextStyle(
                              color: AppTheme.textSecond,
                              fontSize: 11,
                              letterSpacing: 1.5,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _alarmAudioPath != null
                                ? _alarmAudioPath!.split('/').last
                                : 'No custom sound set',
                            style: TextStyle(
                              color: _alarmAudioPath != null
                                  ? AppTheme.textPrimary
                                  : AppTheme.textSecond,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: _pickAudioFile,
                      child: Text(
                        _alarmAudioPath != null ? 'CHANGE' : 'SELECT',
                        style: const TextStyle(
                            color: AppTheme.pink, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // Info blurb
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: AppTheme.primary.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppTheme.primary.withValues(alpha: 0.15),
                  ),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.info_outline, color: AppTheme.primary, size: 16),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'SmartWake detects sleep onset then back-calculates the nearest full 90-min cycle before your deadline.',
                        style: TextStyle(
                          color: AppTheme.textSecond,
                          fontSize: 12,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
