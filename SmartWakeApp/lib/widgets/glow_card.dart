import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Glassmorphism-style card with soft glow border.
class GlowCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final Color? glowColor;
  final double radius;

  const GlowCard({
    super.key,
    required this.child,
    this.padding,
    this.glowColor,
    this.radius = 16,
  });

  @override
  Widget build(BuildContext context) {
    final glow = glowColor ?? AppTheme.primary;
    return Container(
      padding: padding ?? const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.surface.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: glow.withValues(alpha: 0.18), width: 1),
        boxShadow: [
          BoxShadow(
            color: glow.withValues(alpha: 0.12),
            blurRadius: 24,
            spreadRadius: 2,
          ),
        ],
      ),
      child: child,
    );
  }
}
