import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:smart_wake_app/services/storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('benchmark StorageService read', () async {
    SharedPreferences.setMockInitialValues({'device_id': 'test_device_id'});
    await StorageService.init();

    // Warmup
    for (int i = 0; i < 1000; i++) {
      await StorageService.getDeviceId();
    }

    final stopwatch = Stopwatch()..start();
    for (int i = 0; i < 10000; i++) {
      await StorageService.getDeviceId();
    }
    stopwatch.stop();
    print('Benchmark time for 10000 reads: ${stopwatch.elapsedMicroseconds} us');
  });

  test('benchmark StorageService write', () async {
    SharedPreferences.setMockInitialValues({'device_id': 'test_device_id'});
    try { await StorageService.init(); } catch (e) {}

    // Warmup
    for (int i = 0; i < 100; i++) {
      await StorageService.setDeviceId('test_id_$i');
    }

    final stopwatch = Stopwatch()..start();
    for (int i = 0; i < 1000; i++) {
      await StorageService.setDeviceId('test_id_$i');
    }
    stopwatch.stop();
    print('Benchmark time for 1000 writes: ${stopwatch.elapsedMicroseconds} us');
  });
}
