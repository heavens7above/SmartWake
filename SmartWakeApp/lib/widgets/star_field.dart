import 'dart:math';
import 'package:flutter/material.dart';

/// Animated star field — painted as a static backdrop on all screens.
class StarField extends StatefulWidget {
  final Widget child;
  const StarField({super.key, required this.child});

  @override
  State<StarField> createState() => _StarFieldState();
}

class _StarFieldState extends State<StarField>
    with SingleTickerProviderStateMixin {
  late final List<_Star> _stars;
  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    final rng = Random(42);
    _stars = List.generate(
      120,
      (_) => _Star(
        x: rng.nextDouble(),
        y: rng.nextDouble(),
        radius: rng.nextDouble() * 1.4 + 0.4,
        phase: rng.nextDouble() * 2 * pi,
        speed: rng.nextDouble() * 0.6 + 0.4,
      ),
    );
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) => CustomPaint(
            painter: _StarPainter(_stars, _ctrl.value),
            child: const SizedBox.expand(),
          ),
        ),
        widget.child,
      ],
    );
  }
}

class _Star {
  final double x, y, radius, phase, speed;
  const _Star({
    required this.x,
    required this.y,
    required this.radius,
    required this.phase,
    required this.speed,
  });
}

class _StarPainter extends CustomPainter {
  final List<_Star> stars;
  final double t;

  const _StarPainter(this.stars, this.t);

  @override
  void paint(Canvas canvas, Size size) {
    const twoPi = 2 * pi;
    final double twoPiT = twoPi * t;
    for (final s in stars) {
      final flicker = 0.5 + 0.5 * sin(twoPiT * s.speed + twoPi * s.phase);
      final paint = Paint()
        ..color = Colors.white.withValues(alpha: 0.1 + 0.6 * flicker)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, s.radius * 0.5);
      canvas.drawCircle(
        Offset(s.x * size.width, s.y * size.height),
        s.radius * flicker,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_StarPainter old) => old.t != t;
}
