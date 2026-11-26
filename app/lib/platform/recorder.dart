import 'dart:async';
import 'dart:typed_data';

import 'package:record/record.dart';

class RecorderException implements Exception {
  RecorderException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// One finished recording: mono 16-bit PCM.
class Recording {
  Recording(this.pcm, this.sampleRate, this.wallTime);
  final Int16List pcm;
  final int sampleRate; // the rate we asked for
  final Duration wallTime; // how long the mic was open

  /// Samples per second actually delivered, measured against the clock.
  /// Should be close to [sampleRate]; a big gap means the mic ignored our request.
  int get measuredRate => wallTime.inMilliseconds < 500 ? sampleRate : (pcm.length * 1000 ~/ wallTime.inMilliseconds);
}

/// Microphone capture as a 16 kHz mono PCM16 stream (record package, Windows Media Foundation).
/// The stream is fully closed after every recording so Windows' mic indicator goes away.
class Recorder {
  static const int sampleRate = 16000;

  final AudioRecorder _rec = AudioRecorder();
  final BytesBuilder _bytes = BytesBuilder(copy: false);
  final StreamController<double> _level = StreamController<double>.broadcast();
  StreamSubscription<Uint8List>? _sub;
  DateTime? _startedAt;
  int? _carry; // a byte left over when a chunk ends mid-sample

  /// Live mic level, 0.0 to 1.0 (peak of each chunk).
  Stream<double> get level => _level.stream;

  bool get isRecording => _sub != null;

  Future<List<InputDevice>> devices() => _rec.listInputDevices();

  Future<void> start({String? deviceId}) async {
    if (isRecording) return;
    if (!await _rec.hasPermission()) {
      throw RecorderException('Microphone access is blocked. Open Windows Settings > Privacy & security > '
          'Microphone and allow desktop apps to use it.');
    }
    InputDevice? device;
    if (deviceId != null) {
      for (final d in await devices()) {
        if (d.id == deviceId) device = d;
      }
    }
    final Stream<Uint8List> stream;
    try {
      stream = await _rec.startStream(RecordConfig(
          encoder: AudioEncoder.pcm16bits, sampleRate: sampleRate, numChannels: 1, device: device));
    } catch (e) {
      throw RecorderException('Could not open the microphone: $e');
    }
    _bytes.clear();
    _carry = null;
    _startedAt = DateTime.now();
    _sub = stream.listen(_onChunk);
  }

  void _onChunk(Uint8List chunk) {
    _bytes.add(chunk);
    // Level meter: peak of this chunk, handling a sample split across chunks.
    var start = 0;
    var peak = 0;
    if (_carry != null && chunk.isNotEmpty) {
      peak = _abs16(_carry!, chunk[0]);
      start = 1;
      _carry = null;
    }
    final end = start + ((chunk.length - start) & ~1);
    for (var i = start; i < end; i += 2) {
      final a = _abs16(chunk[i], chunk[i + 1]);
      if (a > peak) peak = a;
    }
    if (end < chunk.length) _carry = chunk[end];
    _level.add(peak / 32768.0);
  }

  static int _abs16(int lo, int hi) {
    final v = ((hi << 8) | lo).toSigned(16);
    return v < 0 ? -v : v;
  }

  Future<Recording> stop() async {
    if (!isRecording) throw RecorderException('Not recording.');
    await _rec.stop(); // flushes the last chunk and closes the mic
    await _sub?.cancel();
    _sub = null;
    final wall = DateTime.now().difference(_startedAt!);
    final raw = _bytes.takeBytes();
    final even = Uint8List.fromList(raw.sublist(0, raw.length & ~1)); // fresh, aligned copy
    _level.add(0);
    return Recording(Int16List.view(even.buffer), sampleRate, wall);
  }

  /// Records for a fixed time (used by "Test mic").
  Future<Recording> recordFor(Duration d, {String? deviceId}) async {
    await start(deviceId: deviceId);
    await Future<void>.delayed(d);
    return stop();
  }

  Future<void> dispose() async {
    if (isRecording) await stop();
    await _rec.dispose();
    await _level.close();
  }
}
