import 'dart:typed_data';

import 'errors.dart';
import 'filters.dart';
import 'providers/providers.dart';
import 'wav.dart';

enum DictationMode { raw, clean }

enum DictationOutcome {
  /// Text is ready to paste.
  ok,

  /// Mic was (nearly) silent; nothing was sent.
  silent,

  /// Whisper returned nothing.
  nothingHeard,

  /// Whisper returned a known silence phrase ("thank you for watching").
  hallucination,

  /// A provider failed; see [DictationResult.error].
  error,
}

class DictationResult {
  DictationResult(this.outcome, {this.text = '', this.error, required this.log});
  final DictationOutcome outcome;
  final String text;
  final ProviderError? error;
  final List<String> log;
}

/// Record -> silence check -> Whisper -> hallucination check -> (clean mode) cleanup.
/// Same behaviour as `App.process` in the prototype. Pasting happens outside this class.
class DictationPipeline {
  DictationPipeline({required this.stt, required this.sttOptions, this.cleanup, this.cleanupOptions});

  final SpeechToText stt;
  final SttOptions sttOptions;
  final TextCleanup? cleanup; // null when no key is set for the cleanup provider
  final CleanupOptions? cleanupOptions;

  Future<DictationResult> process(Int16List pcm, int sampleRate, DictationMode mode) async {
    final log = <String>[];
    final length = pcmDuration(pcm.length, sampleRate);
    final peak = peakAmplitude(pcm);
    if (isSilent(peak)) {
      log.add('No voice heard (mic level $peak), nothing sent. Speak a bit louder or check the mic.');
      return DictationResult(DictationOutcome.silent, log: log);
    }

    final String heard;
    try {
      log.add('Sending ${(length.inMilliseconds / 1000).toStringAsFixed(1)} s of audio to ${stt.id} / ${sttOptions.model}, language: ${(sttOptions.language ?? '').isEmpty ? 'auto' : sttOptions.language}');
      heard = (await stt.transcribe(pcm16ToWav(pcm, sampleRate), sttOptions)).text;
    } on ProviderError catch (e) {
      log.add('ERROR: $e');
      return DictationResult(DictationOutcome.error, error: e, log: log);
    }
    log.add('Heard: ${heard.isEmpty ? '(nothing)' : heard}');
    if (heard.isEmpty) return DictationResult(DictationOutcome.nothingHeard, log: log);
    if (isHallucination(heard, length)) {
      log.add('Ignored "$heard": Whisper invents this when it hears silence or noise.');
      return DictationResult(DictationOutcome.hallucination, log: log);
    }

    var text = heard;
    if (mode == DictationMode.clean) {
      if (cleanup == null || cleanupOptions == null) {
        log.add('Cleanup skipped: no key for the cleanup provider. Typing the raw text instead.');
      } else {
        try {
          text = await cleanup!.clean(heard, cleanupOptions!);
          log.add('Cleaned: $text');
        } on ProviderError catch (e) {
          log.add('Cleanup failed, typing raw text instead. ($e)');
        }
      }
    }
    return DictationResult(DictationOutcome.ok, text: text, log: log);
  }
}
