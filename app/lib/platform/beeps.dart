import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'package:audioplayers/audioplayers.dart';

import '../core/wav.dart';

/// High beep when recording starts, low beep when it stops (same tones as the prototype:
/// 880 Hz and 500 Hz, 90 ms). The tones are generated once into temp WAV files.
class Beeps {
  final _player = AudioPlayer();
  String? _startPath;
  String? _stopPath;

  Future<String> _tone(String name, double freq) async {
    const rate = 22050;
    const ms = 90;
    final n = rate * ms ~/ 1000;
    final s = Int16List(n);
    for (var i = 0; i < n; i++) {
      final fade = min(1.0, min(i, n - i) / (rate * 0.008)); // 8 ms fade: no clicks
      s[i] = (sin(2 * pi * freq * i / rate) * 9000 * fade).round();
    }
    final f = File('${Directory.systemTemp.path}${Platform.pathSeparator}mimnets_$name.wav');
    await f.writeAsBytes(pcm16ToWav(s, rate));
    return f.path;
  }

  Future<void> _play(String path) async {
    try {
      await _player.stop();
      await _player.play(DeviceFileSource(path));
    } catch (_) {
      // a missing beep must never break dictation
    }
  }

  Future<void> start() async => _play(_startPath ??= await _tone('beep_start', 880));
  Future<void> stop() async => _play(_stopPath ??= await _tone('beep_stop', 500));

  Future<void> dispose() => _player.dispose();
}
