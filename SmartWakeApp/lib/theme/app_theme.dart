import 'package:flutter/material.dart';

class AppTheme {
  static const Color background  = Color(0xFF080C18);
  static const Color surface     = Color(0xFF0F1628);
  static const Color surfaceAlt  = Color(0xFF141E38);
  static const Color primary     = Color(0xFF7B5CFF);
  static const Color primaryDim  = Color(0xFF3D2E88);
  static const Color cyan        = Color(0xFF00D4FF);
  static const Color teal        = Color(0xFF00C9A7);
  static const Color pink        = Color(0xFFFF6B9D);
  static const Color success     = Color(0xFF00E676);
  static const Color warning     = Color(0xFFFFB74D);
  static const Color textPrimary = Color(0xFFE8E8FF);
  static const Color textSecond  = Color(0xFF8B9CC8);
  static const Color border      = Color(0xFF1E2D54);

  static ThemeData get darkTheme => ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: background,
    colorScheme: const ColorScheme.dark(
      surface: surface,
      primary: primary,
      secondary: cyan,
      error: pink,
      onSurface: textPrimary,
      onPrimary: Colors.white,
    ),
    useMaterial3: true,
    appBarTheme: const AppBarTheme(
      backgroundColor: background,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        color: textPrimary,
        fontSize: 18,
        fontWeight: FontWeight.w600,
        letterSpacing: 1.5,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: primary.withValues(alpha: 0.18),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const IconThemeData(color: primary, size: 24);
        }
        return const IconThemeData(color: Color(0xFF3A4A6A), size: 24);
      }),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return const TextStyle(color: primary, fontSize: 11, fontWeight: FontWeight.w600);
        }
        return const TextStyle(color: Color(0xFF3A4A6A), fontSize: 11);
      }),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primary,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        elevation: 8,
        shadowColor: primary.withValues(alpha: 0.4),
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 16),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: 0.5),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surfaceAlt,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: primary, width: 1.5),
      ),
      labelStyle: const TextStyle(color: textSecond),
      hintStyle: const TextStyle(color: Color(0xFF3A4A6A)),
    ),
  );
}
