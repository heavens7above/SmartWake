import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';
import '../widgets/glow_card.dart';
import '../widgets/star_field.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _apiCtrl = TextEditingController();
  final _urlCtrl = TextEditingController();
  final _devCtrl = TextEditingController();
  bool _healthOk = false;
  bool _checking = false;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _apiCtrl.dispose();
    _urlCtrl.dispose();
    _devCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final apiKey = await StorageService.getApiKey();
    final baseUrl = await StorageService.getBaseUrl();
    final deviceId = await StorageService.getDeviceId();
    if (!mounted) return;
    _apiCtrl.text = apiKey;
    _urlCtrl.text = baseUrl;
    _devCtrl.text = deviceId;
  }

  Future<void> _save() async {
    await StorageService.setApiKey(_apiCtrl.text.trim());
    await StorageService.setBaseUrl(_urlCtrl.text.trim());
    await StorageService.setDeviceId(_devCtrl.text.trim());
    if (!mounted) return;
    setState(() => _saved = true);
    await Future.delayed(const Duration(seconds: 2));
    if (mounted) setState(() => _saved = false);
  }

  Future<void> _ping() async {
    setState(() => _checking = true);
    final ok = await ApiService.checkHealth();
    if (!mounted) return;
    setState(() {
      _checking = false;
      _healthOk = ok;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok ? '✅ Server reachable' : '❌ Could not reach server'),
        backgroundColor: ok ? AppTheme.teal : AppTheme.pink,
      ),
    );
  }

  Future<void> _resetDevice() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppTheme.surface,
        title: const Text(
          'Reset Device ID?',
          style: TextStyle(color: AppTheme.textPrimary),
        ),
        content: const Text(
          'This will generate a new device ID. Your history on the server will be unlinked.',
          style: TextStyle(color: AppTheme.textSecond),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.pink),
            child: const Text('RESET'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await StorageService.resetDeviceId();
      _devCtrl.text = await StorageService.getDeviceId();
      if (mounted) setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return StarField(
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 24),
              const Text(
                'SETTINGS',
                style: TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 2,
                ),
              ),
              const Text(
                'Server & device configuration',
                style: TextStyle(color: AppTheme.textSecond, fontSize: 13),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      GlowCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'CONNECTION',
                              style: TextStyle(
                                color: AppTheme.textSecond,
                                fontSize: 11,
                                letterSpacing: 1.5,
                              ),
                            ),
                            const SizedBox(height: 16),
                            TextField(
                              controller: _urlCtrl,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                              ),
                              decoration: const InputDecoration(
                                labelText: 'Server Base URL',
                                prefixIcon: Icon(
                                  Icons.cloud_outlined,
                                  color: AppTheme.primary,
                                  size: 20,
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextField(
                              controller: _apiCtrl,
                              obscureText: true,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                              ),
                              decoration: const InputDecoration(
                                labelText: 'API Key',
                                prefixIcon: Icon(
                                  Icons.key_outlined,
                                  color: AppTheme.primary,
                                  size: 20,
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            SizedBox(
                              width: double.infinity,
                              child: OutlinedButton.icon(
                                onPressed: _checking ? null : _ping,
                                icon: _checking
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: AppTheme.cyan,
                                        ),
                                      )
                                    : Icon(
                                        _healthOk
                                            ? Icons.check_circle_outline
                                            : Icons.wifi,
                                        color: AppTheme.cyan,
                                      ),
                                label: Text(
                                  _checking ? 'Checking...' : 'Test Connection',
                                  style: const TextStyle(color: AppTheme.cyan),
                                ),
                                style: OutlinedButton.styleFrom(
                                  side: const BorderSide(color: AppTheme.cyan),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 16),

                      GlowCard(
                        glowColor: AppTheme.cyan,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'DEVICE',
                              style: TextStyle(
                                color: AppTheme.textSecond,
                                fontSize: 11,
                                letterSpacing: 1.5,
                              ),
                            ),
                            const SizedBox(height: 16),
                            TextField(
                              controller: _devCtrl,
                              style: const TextStyle(
                                color: AppTheme.textPrimary,
                                fontSize: 12,
                              ),
                              decoration: InputDecoration(
                                labelText: 'Device ID',
                                prefixIcon: const Icon(
                                  Icons.smartphone,
                                  color: AppTheme.cyan,
                                  size: 20,
                                ),
                                suffixIcon: IconButton(
                                  icon: const Icon(
                                    Icons.copy,
                                    color: AppTheme.textSecond,
                                    size: 18,
                                  ),
                                  onPressed: () {
                                    Clipboard.setData(
                                      ClipboardData(text: _devCtrl.text),
                                    );
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Device ID copied'),
                                      ),
                                    );
                                  },
                                ),
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextButton.icon(
                              onPressed: _resetDevice,
                              icon: const Icon(
                                Icons.refresh,
                                color: AppTheme.pink,
                                size: 18,
                              ),
                              label: const Text(
                                'Reset Device ID',
                                style: TextStyle(color: AppTheme.pink),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 20),

                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: _save,
                          icon: Icon(
                            _saved ? Icons.check : Icons.save_outlined,
                          ),
                          label: Text(_saved ? 'SAVED!' : 'SAVE SETTINGS'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _saved
                                ? AppTheme.teal
                                : AppTheme.primary,
                          ),
                        ),
                      ),

                      const SizedBox(height: 24),

                      // Version info
                      const Text(
                        'SmartWake  v1.0.0',
                        style: TextStyle(
                          color: AppTheme.border,
                          fontSize: 11,
                          letterSpacing: 1,
                        ),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'ML-powered sleep intelligence',
                        style: TextStyle(color: AppTheme.border, fontSize: 10),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
