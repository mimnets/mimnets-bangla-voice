// Live check of the app's Groq code (no UI needed).
//
// Reads GROQ_API_KEY from the environment or from the repo-root .env file, sends a WAV
// file to Groq Whisper, then runs the English cleanup on the result.
//
//   cd app
//   dart run tool/groq_smoke.dart ..\voice-clone-lab\out\banglabox\<file>.wav
import 'dart:io';

import 'package:mimnets_bangla_voice/core/errors.dart';
import 'package:mimnets_bangla_voice/core/filters.dart';
import 'package:mimnets_bangla_voice/core/providers/groq.dart';
import 'package:mimnets_bangla_voice/core/providers/providers.dart';
import 'package:mimnets_bangla_voice/core/settings.dart';

String? readKey() {
  final env = Platform.environment['GROQ_API_KEY'];
  if (env != null && env.isNotEmpty) return env;
  for (final path in ['../.env', '.env']) {
    final f = File(path);
    if (!f.existsSync()) continue;
    for (final line in f.readAsLinesSync()) {
      final m = RegExp(r'^\s*GROQ_API_KEY\s*=\s*(.*?)\s*$').firstMatch(line);
      if (m != null && m.group(1)!.isNotEmpty) return m.group(1)!.replaceAll('"', '');
    }
  }
  return null;
}

Future<void> main(List<String> args) async {
  if (args.isEmpty) {
    stderr.writeln('Usage: dart run tool/groq_smoke.dart <file.wav>');
    exit(2);
  }
  final key = readKey();
  if (key == null) {
    stderr.writeln('No GROQ_API_KEY. Put it in the .env file in the repo root.');
    exit(2);
  }
  final wav = File(args.first).readAsBytesSync();
  final s = AppSettings();
  try {
    for (final lang in ['bn', '']) {
      final t = await GroqSpeechToText(apiKey: key)
          .transcribe(wav, SttOptions(model: s.sttModel, language: lang, prompt: s.sttPrompt));
      stdout.writeln('Whisper (${lang.isEmpty ? 'auto' : lang}): ${t.text}');
      if (lang == 'bn') {
        stdout.writeln('Hallucination filter says: ${isHallucination(t.text, const Duration(seconds: 30)) ? 'DROP' : 'keep'}');
        final cleaned = await GroqCleanup(apiKey: key)
            .clean(t.text, CleanupOptions(model: s.cleanupModel, promptTemplate: s.cleanupPrompt));
        stdout.writeln('Cleanup (${s.cleanupModel}): $cleaned');
      }
    }
    stdout.writeln('OK: the app\'s Groq code works.');
  } on ProviderError catch (e) {
    stderr.writeln('FAILED: ${e.userMessage}\n$e');
    exit(1);
  }
}
