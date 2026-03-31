import 'package:flutter/material.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'theme/app_theme.dart';
import 'screens/shell_screen.dart';
import 'services/monitor_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterForegroundTask.initCommunicationPort();
  MonitorService.init();
  runApp(const SmartWakeApp());
}

class SmartWakeApp extends StatelessWidget {
  const SmartWakeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartWake',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      home: const ShellScreen(),
    );
  }
}
