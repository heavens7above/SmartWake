import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:audioplayers/audioplayers.dart';
import '../theme/app_theme.dart';
import '../services/storage_service.dart';
import '../services/api_service.dart';

/// Full-screen alarm overlay that appears when the alarm fires.
/// Shows over lock screen (configured via AndroidManifest).
class AlarmTriggerScreen extends StatefulWidget {
  final String? alarmTime;
  const AlarmTriggerScreen({super.key, this.alarmTime});

  @override
  State<AlarmTriggerScreen> createState() => _AlarmTriggerScreenState();
}

class _AlarmTriggerScreenState extends State<AlarmTriggerScreen>
    with SingleTickerProviderStateMixin {
  final _audio = AudioPlayer();
  late AnimationController _pulseCtrl;
  late Animation<double> _pulseAnim;
  Timer? _clockTimer;
  String _currentTime = '';

  @override
  void initState() {
    super.initState();

    // Force full-screen immersive mode
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _pulseAnim = Tween<double>(begin: 0.85, end: 1.0).animate(
      CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut),
    );

    _updateClock();
    _clockTimer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => _updateClock(),
    );

    _playAlarm();
  }

  void _updateClock() {
    final now = TimeOfDay.now();
    final h = now.hour.toString().padLeft(2, '0');
    final m = now.minute.toString().padLeft(2, '0');
    if (mounted) setState(() => _currentTime = '$h:$m');
  }

  Future<void> _playAlarm() async {
    final path = StorageService.getAlarmAudioPath();
    if (path != null && path.isNotEmpty) {
      await _audio.setReleaseMode(ReleaseMode.loop);
      await _audio.play(DeviceFileSource(path));
    }
  }

  Future<void> _dismiss() async {
    await _audio.stop();

    // Acknowledge wake to server
    final deviceId = StorageService.getDeviceId();
    final acked = await ApiService.ackWake(deviceId);

    // Restore system UI
    SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.manual,
      overlays: SystemUiOverlay.values,
    );

    if (mounted) Navigator.of(context).pop(acked);
  }

  @override
  void dispose() {
    _clockTimer?.cancel();
    _pulseCtrl.dispose();
    _audio.stop();
    _audio.dispose();
    SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.manual,
      overlays: SystemUiOverlay.values,
    );
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppTheme.background,
        body: Container(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: Alignment.center,
              radius: 1.2,
              colors: [
                AppTheme.pink.withValues(alpha: 0.10),
                AppTheme.background,
              ],
            ),
          ),
          child: SafeArea(
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Spacer(flex: 2),

                  // Pulsing alarm icon
                  AnimatedBuilder(
                    animation: _pulseAnim,
                    builder: (_, child) => Transform.scale(
                      scale: _pulseAnim.value,
                      child: child,
                    ),
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            AppTheme.pink.withValues(alpha: 0.25),
                            AppTheme.pink.withValues(alpha: 0.05),
                          ],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppTheme.pink.withValues(alpha: 0.4),
                            blurRadius: 50,
                            spreadRadius: 10,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.alarm,
                        color: AppTheme.pink,
                        size: 56,
                      ),
                    ),
                  ),

                  const SizedBox(height: 40),

                  // Current time
                  Text(
                    _currentTime,
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 72,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 4,
                    ),
                  ),

                  const SizedBox(height: 8),

                  const Text(
                    'WAKE UP',
                    style: TextStyle(
                      color: AppTheme.pink,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 6,
                    ),
                  ),

                  const SizedBox(height: 4),

                  Text(
                    'Optimal sleep cycle complete',
                    style: TextStyle(
                      color: AppTheme.textSecond.withValues(alpha: 0.7),
                      fontSize: 13,
                    ),
                  ),

                  const Spacer(flex: 3),

                  // DISMISS button
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 48),
                    child: SizedBox(
                      width: double.infinity,
                      height: 64,
                      child: ElevatedButton(
                        onPressed: _dismiss,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppTheme.pink,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(32),
                          ),
                          elevation: 12,
                          shadowColor: AppTheme.pink.withValues(alpha: 0.5),
                        ),
                        child: const Text(
                          'DISMISS',
                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 4,
                          ),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 48),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
