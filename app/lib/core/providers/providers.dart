import 'dart:typed_data';

/// Provider interfaces. Every cloud service sits behind one of these so it can be
/// swapped from Settings. See docs/ARCHITECTURE.md section 2.

class SttOptions {
  const SttOptions({required this.model, this.language, this.prompt});
  final String model;
  final String? language; // 'bn', 'en', or null/empty for auto
  final String? prompt; // vocabulary hint (Groq: max 224 tokens)
}

class Transcript {
  const Transcript(this.text, this.model);
  final String text;
  final String model;
}

/// Speech to text. Groq Whisper today; OpenRouter, Sarvam or local later.
abstract class SpeechToText {
  String get id;
  Future<Transcript> transcribe(Uint8List wav, SttOptions options);
}

class CleanupOptions {
  const CleanupOptions({required this.model, required this.promptTemplate});
  final String model;
  final String promptTemplate; // contains ${output} where the dictated text goes
}

/// Turns raw dictation into a clear English instruction.
abstract class TextCleanup {
  String get id;
  Future<String> clean(String text, CleanupOptions options);
}

/// A cloned voice: reference clip plus what was said in it.
class VoiceProfile {
  const VoiceProfile({required this.id, required this.name, required this.wavPath, this.transcript = ''});
  final String id; // sha256 of the WAV bytes
  final String name;
  final String wavPath;
  final String transcript;
}

class CloneSettings {
  const CloneSettings({this.cfgWeight = 0.8, this.exaggeration = 0.5, this.temperature = 0.5, this.seed = 0});
  final double cfgWeight;
  final double exaggeration;
  final double temperature;
  final int seed;
}

class SpeechAudio {
  const SpeechAudio(this.samples, this.sampleRate);
  final Float32List samples;
  final int sampleRate;
}

/// Speak text in a cloned voice, one sentence per call (the app joins them).
abstract class VoiceCloneTts {
  String get id;
  Future<void> warmUp();
  Future<SpeechAudio> speakSentence(String sentence, VoiceProfile voice, CloneSettings settings);
}
