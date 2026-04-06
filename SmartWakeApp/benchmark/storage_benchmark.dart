import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../lib/services/storage_service.dart';

void main() {
  test('StorageService Performance Benchmark', () async {
    SharedPreferences.setMockInitialValues({'device_id': 'test_id'});
    await StorageService.init();

    // Warmup
    for (int i = 0; i < 1000; i++) {
      StorageService.getDeviceId();
    }

    final sw = Stopwatch()..start();
    for (int i = 0; i < 10000; i++) {
      StorageService.getDeviceId();
    }
    sw.stop();

    print('Baseline: ${sw.elapsedMicroseconds} microseconds for 10000 calls');
  });
}
