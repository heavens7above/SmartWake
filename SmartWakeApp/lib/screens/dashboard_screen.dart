import 'dart:async';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../widgets/glow_card.dart';
import '../widgets/star_field.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../models/models.dart';

String _formatDateTimeLabel(
  String? value, {
  int fallbackLength = 19,
  int parsedLength = 16,
}) {
  if (value == null || value.isEmpty) return 'Unknown';
  final parsed = DateTime.tryParse(value);
  if (parsed != null) {
    final iso = parsed.toLocal().toIso8601String().replaceFirst('T', ' ');
    return iso.length > parsedLength ? iso.substring(0, parsedLength) : iso;
  }
  final normalized = value.replaceFirst('T', ' ');
  return normalized.length > fallbackLength
      ? normalized.substring(0, fallbackLength)
      : normalized;
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  DashboardData? _data;
  bool _loading = true;
  int? _pendingRating;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load(showLoading: true);
    _timer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _load(showLoading: false),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool showLoading = true}) async {
    if (showLoading) setState(() => _loading = true);
    final id = await StorageService.getDeviceId();
    final data = await ApiService.getDashboard(id);
    if (mounted) {
      setState(() {
        _data = data;
        _loading = false;
      });
    }
  }

  Future<void> _submitRating(int stars) async {
    final id = await StorageService.getDeviceId();
    setState(() => _pendingRating = stars);
    final ok = await ApiService.submitRating(id, stars);
    if (mounted) {
      final session = _data?.recentSession;
      setState(() {
        _pendingRating = null;
        if (ok && session != null) {
          _data = DashboardData(
            deviceId: _data!.deviceId,
            recentSession: SleepSession(
              id: session.id,
              onsetTime: session.onsetTime,
              wakeDeadline: session.wakeDeadline,
              alarmTime: session.alarmTime,
              alarmFired: session.alarmFired,
              qualityRating: stars,
              createdAt: session.createdAt,
            ),
            logs: _data!.logs,
          );
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? '⭐ Rating saved' : '❌ Failed to save rating'),
          backgroundColor: ok ? AppTheme.teal : AppTheme.pink,
        ),
      );
      if (ok) _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return StarField(
      child: SafeArea(
        child: RefreshIndicator(
          onRefresh: _load,
          color: AppTheme.primary,
          backgroundColor: AppTheme.surface,
          child: _loading
              ? const Center(
                  child: CircularProgressIndicator(color: AppTheme.primary),
                )
              : _data == null
                  ? const Center(
                      child: Text(
                        'Could not load data',
                        style: TextStyle(color: AppTheme.textSecond),
                      ),
                    )
                  : CustomScrollView(
                      slivers: [
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(20, 24, 20, 0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'SLEEP HISTORY',
                                  style: TextStyle(
                                    color: AppTheme.textPrimary,
                                    fontSize: 22,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 2,
                                  ),
                                ),
                                const Text(
                                  'Last session & telemetry logs',
                                  style: TextStyle(
                                    color: AppTheme.textSecond,
                                    fontSize: 13,
                                  ),
                                ),
                                const SizedBox(height: 20),

                                // Most recent session
                                if (_data!.recentSession != null)
                                  _SessionCard(
                                    session: _data!.recentSession!,
                                    onRate: _submitRating,
                                    pending: _pendingRating,
                                  )
                                else
                                  const GlowCard(
                                    child: Center(
                                      child: Padding(
                                        padding: EdgeInsets.all(12),
                                        child: Text(
                                          'No sessions recorded yet',
                                          style: TextStyle(
                                            color: AppTheme.textSecond,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ),

                                const SizedBox(height: 20),
                                const Text(
                                  'TELEMETRY LOG',
                                  style: TextStyle(
                                    color: AppTheme.textSecond,
                                    fontSize: 11,
                                    letterSpacing: 1.5,
                                  ),
                                ),
                                const SizedBox(height: 10),
                              ],
                            ),
                          ),
                        ),
                        SliverList(
                          delegate: SliverChildBuilderDelegate((ctx, i) {
                            final entry = _data!.logs[i];
                            final prob = entry.sleepProb ?? 0.0;
                            return Padding(
                              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                              child: Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: AppTheme.surface,
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(color: AppTheme.border),
                                ),
                                child: Row(
                                  children: [
                                    Icon(
                                      prob > 0.75
                                          ? Icons.bedtime
                                          : (prob > 0.4
                                              ? Icons.bedtime_outlined
                                              : Icons.visibility),
                                      color: prob > 0.75
                                          ? AppTheme.teal
                                          : (prob > 0.4
                                              ? AppTheme.primary
                                              : AppTheme.textSecond),
                                      size: 18,
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            _formatDateTimeLabel(
                                              entry.timestamp,
                                              parsedLength: 19,
                                            ),
                                            style: const TextStyle(
                                              color: AppTheme.textPrimary,
                                              fontSize: 12,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                          Text(
                                            'mag: ${entry.accelMagnitude.toStringAsFixed(3)}  ${entry.charging ? "⚡" : "🔋"}',
                                            style: const TextStyle(
                                              color: AppTheme.textSecond,
                                              fontSize: 11,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.end,
                                      children: [
                                        Text(
                                          '${(prob * 100).toStringAsFixed(0)}%',
                                          style: TextStyle(
                                            color: prob > 0.75
                                                ? AppTheme.teal
                                                : (prob > 0.4
                                                    ? AppTheme.primary
                                                    : AppTheme.textSecond),
                                            fontSize: 14,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        const Text(
                                          'sleep',
                                          style: TextStyle(
                                            color: AppTheme.textSecond,
                                            fontSize: 10,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }, childCount: _data!.logs.length),
                        ),
                        const SliverToBoxAdapter(child: SizedBox(height: 20)),
                      ],
                    ),
        ),
      ),
    );
  }
}

class _SessionCard extends StatelessWidget {
  final SleepSession session;
  final void Function(int) onRate;
  final int? pending;

  const _SessionCard({
    required this.session,
    required this.onRate,
    this.pending,
  });

  @override
  Widget build(BuildContext context) {
    return GlowCard(
      glowColor: AppTheme.teal,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.nights_stay, color: AppTheme.teal, size: 20),
              const SizedBox(width: 8),
              const Text(
                'RECENT SESSION',
                style: TextStyle(
                  color: AppTheme.textSecond,
                  fontSize: 11,
                  letterSpacing: 1.5,
                ),
              ),
              const Spacer(),
              if (session.alarmFired)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.success.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: AppTheme.success.withValues(alpha: 0.4),
                    ),
                  ),
                  child: const Text(
                    'ALARM FIRED',
                    style: TextStyle(
                      color: AppTheme.success,
                      fontSize: 9,
                      letterSpacing: 1,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          if (session.onsetTime != null)
            _Row(
              icon: Icons.bedtime,
              label: 'Sleep onset',
              value: _formatDateTimeLabel(
                session.onsetTime,
                fallbackLength: 16,
                parsedLength: 16,
              ),
            ),
          if (session.alarmTime != null)
            _Row(
              icon: Icons.alarm,
              label: 'Optimal alarm',
              value: _formatDateTimeLabel(
                session.alarmTime,
                fallbackLength: 16,
                parsedLength: 16,
              ),
            ),
          if (session.wakeDeadline != null)
            _Row(
              icon: Icons.flag_outlined,
              label: 'Deadline',
              value: _formatDateTimeLabel(
                session.wakeDeadline,
                fallbackLength: 16,
                parsedLength: 16,
              ),
            ),
          const Divider(color: AppTheme.border, height: 24),
          const Text(
            'RATE YOUR SLEEP',
            style: TextStyle(
              color: AppTheme.textSecond,
              fontSize: 11,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (i) {
              final star = i + 1;
              final selected = session.qualityRating != null &&
                  star <= session.qualityRating!;
              return GestureDetector(
                onTap: pending == null ? () => onRate(star) : null,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: Icon(
                    selected ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: selected ? AppTheme.warning : AppTheme.border,
                    size: 34,
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final IconData icon;
  final String label, value;
  const _Row({required this.icon, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, color: AppTheme.primary, size: 15),
          const SizedBox(width: 8),
          Text(
            '$label: ',
            style: const TextStyle(color: AppTheme.textSecond, fontSize: 12),
          ),
          Text(
            value,
            style: const TextStyle(
              color: AppTheme.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
