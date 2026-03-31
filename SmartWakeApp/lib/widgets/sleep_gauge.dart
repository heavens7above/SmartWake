import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Semicircular gauge showing sleep probability (0.0 – 1.0).
class SleepGauge extends StatelessWidget {
  final double probability;
  final String stateLabel;

  const SleepGauge({
    super.key,
    required this.probability,
    required this.stateLabel,
  });

  double get _normalizedProbability => probability.clamp(0.0, 1.0).toDouble();

  Color get _arcColor {
    if (_normalizedProbability >= 0.75) return AppTheme.teal;
    if (_normalizedProbability >= 0.5) return AppTheme.primary;
    if (_normalizedProbability >= 0.25) return AppTheme.cyan;
    return AppTheme.textSecond;
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 260,
      height: 180,
      child: CustomPaint(
        painter: _GaugePainter(
            probability: _normalizedProbability, arcColor: _arcColor),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 24),
            Text(
              _normalizedProbability >= 0.75
                  ? '🌙'
                  : (_normalizedProbability >= 0.4 ? '😴' : '👁'),
              style: const TextStyle(fontSize: 44),
            ),
            const SizedBox(height: 8),
            Text(
              '${(_normalizedProbability * 100).toStringAsFixed(0)}%',
              style: TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w800,
                color: _arcColor,
                letterSpacing: 1,
              ),
            ),
            Text(
              stateLabel,
              style: const TextStyle(
                fontSize: 11,
                color: AppTheme.textSecond,
                letterSpacing: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double probability;
  final Color arcColor;

  _GaugePainter({required this.probability, required this.arcColor});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height - 10;
    final radius = size.width / 2 - 10;
    final rect = Rect.fromCircle(center: Offset(cx, cy), radius: radius);

    // Track arc
    final trackPaint = Paint()
      ..color = AppTheme.border
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, math.pi, math.pi, false, trackPaint);

    // Value arc with glow
    final glowPaint = Paint()
      ..color = arcColor.withValues(alpha: 0.3)
      ..strokeWidth = 22
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);
    canvas.drawArc(rect, math.pi, math.pi * probability, false, glowPaint);

    final arcPaint = Paint()
      ..color = arcColor
      ..strokeWidth = 12
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;
    canvas.drawArc(rect, math.pi, math.pi * probability, false, arcPaint);
  }

  @override
  bool shouldRepaint(_GaugePainter old) =>
      old.probability != probability || old.arcColor != arcColor;
}
