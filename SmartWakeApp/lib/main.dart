import 'package:flutter/material.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'theme/app_theme.dart';
import 'screens/shell_screen.dart';
import 'services/monitor_service.dart';
import 'services/storage_service.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await StorageService.init();
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
  final _scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

  @override
  void initState() {
    super.initState();
    _registerDevice();
  }

  Future<void> _registerDevice() async {
    final deviceId = StorageService.getDeviceId();
    final ok = await ApiService.registerDevice(deviceId);
    if (ok) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scaffoldMessengerKey.currentState?.showSnackBar(
        const SnackBar(
          content: Text(
            'Device registration failed. History and alarm sync will stay offline until the server is reachable.',
          ),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SmartWake',
      debugShowCheckedModeBanner: false,
      scaffoldMessengerKey: _scaffoldMessengerKey,
      theme: AppTheme.darkTheme,
      home: const ShellScreen(),
    );
  }
}
