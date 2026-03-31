import 'package:flutter/material.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'theme/app_theme.dart';
import 'screens/shell_screen.dart';
import 'services/monitor_service.dart';
import 'services/storage_service.dart';
import 'services/api_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  FlutterForegroundTask.initCommunicationPort();
  MonitorService.init();
  runApp(const SmartWakeApp());
}

class SmartWakeApp extends StatefulWidget {
  const SmartWakeApp({super.key});

  @override
  State<SmartWakeApp> createState() => _SmartWakeAppState();
}

class _SmartWakeAppState extends State<SmartWakeApp> {
  @override
  void initState() {
    super.initState();
    _registerDevice();
  }

  Future<void> _registerDevice() async {
    final deviceId = await StorageService.getDeviceId();
    await ApiService.registerDevice(deviceId);
  }

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
