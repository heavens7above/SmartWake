import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:permission_handler/permission_handler.dart';
import '../theme/app_theme.dart';
import '../widgets/sleep_gauge.dart';
import '../widgets/glow_card.dart';
import '../widgets/star_field.dart';
import '../services/monitor_service.dart';
import '../services/storage_service.dart';
import 'alarm_trigger_screen.dart';

class SleepScreen extends StatefulWidget {
  const SleepScreen({super.key});

  @override
  State<SleepScreen> createState() => _SleepScreenState();
}

class _SleepScreenState extends State<SleepScreen>
    with TickerProviderStateMixin {
  bool _monitoring = false;
  String _state = 'IDLE';
  double _sleepProb = 0.0;
  String? _onsetTime;
  int _consecutive = 0;
  int _battery = 0;
  bool _charging = false;
  double _accelMag = 0.0;
  DateTime? _lastTelemetryErrorToast;

  late AnimationController _pulseCtrl;
  late Animation<double> _pulseAnim;

  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    _pulseAnim = Tween(
      begin: 1.0,
      end: 1.12,
    ).animate(CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut));
    FlutterForegroundTask.addTaskDataCallback(_onTaskData);
    _loadState();
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    FlutterForegroundTask.removeTaskDataCallback(_onTaskData);
    super.dispose();
  }

  Future<void> _loadState() async {
    final running = await MonitorService.isRunning;
    if (mounted) setState(() => _monitoring = running);
  }

  void _onTaskData(Object data) {
    if (!mounted || data is! Map<Object?, Object?>) return;
    if (data['type'] == 'telemetry') {
      final nextState = data['state'];
      final nextOnsetTime = data['onset_time'];
      final nextConsecutive = data['consecutive'];
      final nextBattery = data['battery'];
      final nextCharging = data['charging'];
      setState(() {
        _state = nextState is String && nextState.isNotEmpty
            ? nextState
            : _state;
        _sleepProb = data['sleep_prob'] is num
            ? (data['sleep_prob'] as num).toDouble()
            : double.tryParse('${data['sleep_prob']}') ?? 0.0;
        _onsetTime = nextOnsetTime is String ? nextOnsetTime : null;
        _consecutive = nextConsecutive is num
            ? nextConsecutive.toInt()
            : int.tryParse('$nextConsecutive') ?? 0;
        _battery = nextBattery is num
            ? nextBattery.toInt()
            : int.tryParse('$nextBattery') ?? _battery;
        _charging = nextCharging is bool
            ? nextCharging
            : '$nextCharging'.toLowerCase() == 'true';
        final x = data['accel_x'] is num
            ? (data['accel_x'] as num).toDouble()
            : 0.0;
        final y = data['accel_y'] is num
            ? (data['accel_y'] as num).toDouble()
            : 0.0;
        final z = data['accel_z'] is num
            ? (data['accel_z'] as num).toDouble()
            : 0.0;
        _accelMag = math.sqrt(x * x + y * y + z * z);
      });
    } else if (data['type'] == 'alarm') {
      _showAlarmDialog(
        data['alarm_time'] is String ? data['alarm_time'] as String : null,
      );
    } else if (data['type'] == 'telemetry_error') {
      final now = DateTime.now();
      if (_lastTelemetryErrorToast == null ||
          now.difference(_lastTelemetryErrorToast!) >
              const Duration(minutes: 2)) {
        _lastTelemetryErrorToast = now;
        final status = data['status'];
        final error = data['error'];
        final msg = status != null
            ? 'Telemetry upload failed (HTTP $status)'
            : (error != null ? 'Telemetry error: $error' : 'Telemetry failed');
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(msg)));
      }
    }
  }

  Future<void> _showAlarmDialog(String? time) async {
    if (!mounted) return;

    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => AlarmTriggerScreen(alarmTime: time),
      ),
    );
  }

  Future<void> _toggleMonitor() async {
    if (_monitoring) {
      await MonitorService.stop();
      await StorageService.setIsMonitoring(false);
      if (!mounted) return;
      setState(() {
        _monitoring = false;
        _state = 'IDLE';
        _sleepProb = 0;
      });
    } else {
      // Request permissions
      await Permission.notification.request();
      await Permission.ignoreBatteryOptimizations.request();

      final result = await MonitorService.start();
      final ok = result is ServiceRequestSuccess;
      if (ok) await StorageService.setIsMonitoring(true);
      if (!mounted) return;
      setState(() => _monitoring = ok);
      if (!ok) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not start monitoring — check permissions'),
          ),
        );
      }
    }
  }

  Color get _stateColor {
    switch (_state) {
      case 'CONFIRMED':
        return AppTheme.teal;
      case 'TRACKING':
        return AppTheme.primary;
      case 'INSUFFICIENT_DATA':
        return AppTheme.warning;
      default:
        return AppTheme.textSecond;
    }
  }

  @override
  Widget build(BuildContext context) {
    return StarField(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              const SizedBox(height: 16),
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'S M A R T W A K E',
                    style: TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 3,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: _stateColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _stateColor.withValues(alpha: 0.4),
                      ),
                    ),
                    child: Text(
                      _state.replaceAll('_', ' '),
                      style: TextStyle(
                        color: _stateColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.5,
                      ),
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 32),

              // Gauge + pulse ring
              AnimatedBuilder(
                animation: _pulseAnim,
                builder: (_, child) => Transform.scale(
                  scale: _monitoring ? _pulseAnim.value : 1.0,
                  child: child,
                ),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: _monitoring
                        ? [
                            BoxShadow(
                              color: AppTheme.primary.withValues(alpha: 0.25),
                              blurRadius: 40,
                              spreadRadius: 10,
                            ),
                          ]
                        : [],
                  ),
                  child: SleepGauge(
                    probability: _sleepProb,
                    stateLabel: _state == 'IDLE'
                        ? 'NOT MONITORING'
                        : _state.replaceAll('_', ' '),
                  ),
                ),
              ),

              const SizedBox(height: 28),

              // Onset time banner
              if (_onsetTime != null)
                GlowCard(
                  glowColor: AppTheme.teal,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.bedtime, color: AppTheme.teal, size: 18),
                      const SizedBox(width: 8),
                      Text(
                        'Sleep onset: $_onsetTime',
                        style: const TextStyle(
                          color: AppTheme.textPrimary,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),

              if (_onsetTime != null) const SizedBox(height: 12),

              // Stats row
              Row(
                children: [
                  _StatChip(
                    label: 'BATTERY',
                    value: '$_battery%',
                    icon: _charging ? Icons.bolt : Icons.battery_std,
                  ),
                  const SizedBox(width: 10),
                  _StatChip(
                    label: 'MOTION',
                    value: '${_accelMag.toStringAsFixed(2)} g',
                    icon: Icons.vibration,
                  ),
                  const SizedBox(width: 10),
                  _StatChip(
                    label: 'STREAK',
                    value: '$_consecutive',
                    icon: Icons.trending_up,
                  ),
                ],
              ),

              const Spacer(),

              // Start / Stop button
              SizedBox(
                width: double.infinity,
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 300),
                  child: _monitoring
                      ? ElevatedButton.icon(
                          key: const ValueKey('stop'),
                          onPressed: _toggleMonitor,
                          icon: const Icon(Icons.stop_circle_outlined),
                          label: const Text('STOP MONITORING'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.pink,
                            shadowColor: AppTheme.pink.withValues(alpha: 0.4),
                          ),
                        )
                      : ElevatedButton.icon(
                          key: const ValueKey('start'),
                          onPressed: _toggleMonitor,
                          icon: const Icon(Icons.play_circle_outline),
                          label: const Text('START MONITORING'),
                        ),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label, value;
  final IconData icon;
  const _StatChip({
    required this.label,
    required this.value,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          children: [
            Icon(icon, color: AppTheme.primary, size: 18),
            const SizedBox(height: 4),
            Text(
              value,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                color: AppTheme.textSecond,
                fontSize: 9,
                letterSpacing: 1,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
