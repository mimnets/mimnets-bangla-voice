import 'dart:typed_data';

/// Wraps mono 16-bit PCM samples in a WAV header (what Groq Whisper expects).
Uint8List pcm16ToWav(Int16List samples, int sampleRate) {
  final dataLen = samples.lengthInBytes;
  final header = ByteData(44);
  void tag(int offset, String s) {
    for (var i = 0; i < s.length; i++) {
      header.setUint8(offset + i, s.codeUnitAt(i));
    }
  }

  tag(0, 'RIFF');
  header.setUint32(4, 36 + dataLen, Endian.little);
  tag(8, 'WAVE');
  tag(12, 'fmt ');
  header.setUint32(16, 16, Endian.little); // fmt chunk size
  header.setUint16(20, 1, Endian.little); // PCM
  header.setUint16(22, 1, Endian.little); // mono
  header.setUint32(24, sampleRate, Endian.little);
  header.setUint32(28, sampleRate * 2, Endian.little); // byte rate
  header.setUint16(32, 2, Endian.little); // block align
  header.setUint16(34, 16, Endian.little); // bits per sample
  tag(36, 'data');
  header.setUint32(40, dataLen, Endian.little);

  final out = Uint8List(44 + dataLen);
  out.setRange(0, 44, header.buffer.asUint8List());
  out.setRange(44, 44 + dataLen, samples.buffer.asUint8List(samples.offsetInBytes, dataLen));
  return out;
}

/// Loudest absolute sample value (0 to 32768).
int peakAmplitude(Int16List samples) {
  var peak = 0;
  for (final v in samples) {
    final a = v < 0 ? -v : v;
    if (a > peak) peak = a;
  }
  return peak;
}

/// Length of [sampleCount] mono samples at [sampleRate].
Duration pcmDuration(int sampleCount, int sampleRate) =>
    Duration(microseconds: sampleCount * 1000000 ~/ sampleRate);
