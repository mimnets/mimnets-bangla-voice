import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:mimnets_bangla_voice/core/errors.dart';
import 'package:mimnets_bangla_voice/core/settings.dart';
import 'package:mimnets_bangla_voice/core/wav.dart';

void main() {
  group('wav', () {
    test('header and data are correct', () {
      final pcm = Int16List.fromList([0, 1000, -2000, 32767, -32768]);
      final wav = pcm16ToWav(pcm, 16000);
      final b = ByteData.sublistView(wav);
      expect(String.fromCharCodes(wav.sublist(0, 4)), 'RIFF');
      expect(String.fromCharCodes(wav.sublist(8, 12)), 'WAVE');
      expect(b.getUint32(4, Endian.little), 36 + 10);
      expect(b.getUint16(22, Endian.little), 1); // mono
      expect(b.getUint32(24, Endian.little), 16000);
      expect(b.getUint16(34, Endian.little), 16);
      expect(b.getUint32(40, Endian.little), 10);
      expect(b.getInt16(44 + 2, Endian.little), 1000);
      expect(b.getInt16(44 + 8, Endian.little), -32768);
      expect(wav.length, 54);
    });

    test('peak and duration', () {
      expect(peakAmplitude(Int16List.fromList([3, -500, 20])), 500);
      expect(peakAmplitude(Int16List.fromList([-32768])), 32768);
      expect(pcmDuration(16000 * 3, 16000), const Duration(seconds: 3));
    });
  });

  group('settings', () {
    test('defaults match prototype and Phase 1', () {
      final s = AppSettings();
      expect(s.sttModel, 'whisper-large-v3');
      expect(s.cleanupModel, 'openai/gpt-oss-120b');
      expect(s.hotkeyRaw, 'ctrl+alt+d');
      expect(s.hotkeyClean, 'ctrl+alt+e');
      expect(s.cloneCfgWeight, 0.8);
      expect(s.sttLanguage, 'bn');
      expect(s.cleanupPrompt, contains(r'${output}'));
    });

    test('round trip', () {
      final s = AppSettings()
        ..sttLanguage = 'bn'
        ..hotkeyClean = 'ctrl+shift+space'
        ..cloneSeed = 3
        ..inputDevice = 'Headset';
      final back = AppSettings.fromJson(s.toJson());
      expect(back.sttLanguage, 'bn');
      expect(back.hotkeyClean, 'ctrl+shift+space');
      expect(back.cloneSeed, 3);
      expect(back.inputDevice, 'Headset');
    });

    test('bad or missing fields keep defaults', () {
      final s = AppSettings.fromJson({'stt.model': 42, 'clone.cfgWeight': 1, 'audio.beep': 'yes'});
      expect(s.sttModel, 'whisper-large-v3');
      expect(s.cloneCfgWeight, 1.0); // int accepted for a double
      expect(s.beep, isTrue);
    });
  });

  group('errors', () {
    test('status codes map to kinds', () {
      expect(ProviderError.fromResponse('Groq', 401, '').kind, ErrorKind.badKey);
      expect(ProviderError.fromResponse('OpenRouter', 402, '').kind, ErrorKind.needsCredit);
      expect(ProviderError.fromResponse('Groq', 413, '').kind, ErrorKind.tooLarge);
      expect(ProviderError.fromResponse('Groq', 503, '').isTransient, isTrue);
      expect(ProviderError.fromResponse('Groq', 498, '').kind, ErrorKind.serverBusy);
    });

    test('429 reads retry-after', () {
      final e = ProviderError.fromResponse('Groq', 429, 'slow down', {'retry-after': '7'});
      expect(e.kind, ErrorKind.rateLimited);
      expect(e.retryAfter, const Duration(seconds: 7));
      expect(e.userMessage, contains('8 s'));
    });

    test('detail is capped at 300 chars', () {
      expect(ProviderError.fromResponse('Groq', 500, 'x' * 1000).detail.length, 300);
    });
  });
}
