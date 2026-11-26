import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mimnets_bangla_voice/core/dictation.dart';
import 'package:mimnets_bangla_voice/core/errors.dart';
import 'package:mimnets_bangla_voice/core/providers/groq.dart';
import 'package:mimnets_bangla_voice/core/providers/providers.dart';

http.Response jsonResponse(Object body, [int status = 200]) => http.Response.bytes(
    utf8.encode(jsonEncode(body)), status,
    headers: {'content-type': 'application/json'}); // no charset on purpose: must still decode Bangla

Int16List loudPcm(int seconds) =>
    Int16List.fromList(List.generate(16000 * seconds, (i) => (i % 40 < 20) ? 8000 : -8000));

void main() {
  group('GroqSpeechToText', () {
    test('sends the prototype form fields and decodes Bangla', () async {
      late http.Request seen;
      final stt = GroqSpeechToText(
          apiKey: 'gsk_test',
          client: MockClient((req) async {
            seen = req;
            return jsonResponse({'text': ' এই ফাইলে একটা login function বানাও '});
          }));
      final t = await stt.transcribe(
          Uint8List(44), const SttOptions(model: 'whisper-large-v3', language: 'bn', prompt: 'VS Code'));
      expect(t.text, 'এই ফাইলে একটা login function বানাও');
      expect(seen.url.toString(), 'https://api.groq.com/openai/v1/audio/transcriptions');
      expect(seen.headers['Authorization'], 'Bearer gsk_test');
      final body = utf8.decode(seen.bodyBytes, allowMalformed: true);
      for (final f in ['name="model"', 'whisper-large-v3', 'name="language"', 'name="prompt"', 'VS Code',
        'name="temperature"', 'name="response_format"', 'filename="audio.wav"']) {
        expect(body, contains(f));
      }
    });

    test('omits language when auto', () async {
      late http.Request seen;
      final stt = GroqSpeechToText(apiKey: 'k', client: MockClient((req) async {
        seen = req;
        return jsonResponse({'text': 'hi'});
      }));
      await stt.transcribe(Uint8List(44), const SttOptions(model: 'whisper-large-v3', language: ''));
      expect(utf8.decode(seen.bodyBytes, allowMalformed: true), isNot(contains('name="language"')));
    });

    test('401 becomes badKey', () async {
      final stt = GroqSpeechToText(apiKey: 'bad', client: MockClient((_) async => jsonResponse({'error': 'x'}, 401)));
      expect(() => stt.transcribe(Uint8List(44), const SttOptions(model: 'm')),
          throwsA(isA<ProviderError>().having((e) => e.kind, 'kind', ErrorKind.badKey)));
    });

    test('network failure becomes offline', () async {
      final stt = GroqSpeechToText(apiKey: 'k', client: MockClient((_) async => throw const SocketException('down')));
      expect(() => stt.transcribe(Uint8List(44), const SttOptions(model: 'm')),
          throwsA(isA<ProviderError>().having((e) => e.kind, 'kind', ErrorKind.offline)));
    });
  });

  group('GroqCleanup', () {
    const opts = CleanupOptions(model: 'openai/gpt-oss-120b', promptTemplate: r'Clean this: ${output}');

    test('fills the template, asks for low reasoning, strips think tags', () async {
      late Map<String, dynamic> sent;
      final c = GroqCleanup(apiKey: 'k', client: MockClient((req) async {
        sent = jsonDecode(req.body) as Map<String, dynamic>;
        return jsonResponse({
          'choices': [
            {'message': {'content': '<think>ok</think>"Create a login function in this file."'}}
          ]
        });
      }));
      expect(await c.clean('ei file e ekta login function banao', opts), 'Create a login function in this file.');
      expect(sent['reasoning_effort'], 'low');
      expect(sent['temperature'], 0.2);
      expect((sent['messages'] as List).first['content'], 'Clean this: ei file e ekta login function banao');
    });

    test('retries without reasoning_effort on a reasoning 400', () async {
      final bodies = <Map<String, dynamic>>[];
      final c = GroqCleanup(apiKey: 'k', client: MockClient((req) async {
        bodies.add(jsonDecode(req.body) as Map<String, dynamic>);
        if (bodies.length == 1) return jsonResponse({'error': 'reasoning_effort is not supported'}, 400);
        return jsonResponse({
          'choices': [
            {'message': {'content': 'Fixed.'}}
          ]
        });
      }));
      expect(await c.clean('x', opts), 'Fixed.');
      expect(bodies, hasLength(2));
      expect(bodies[1].containsKey('reasoning_effort'), isFalse);
    });

    test('template without placeholder appends the text', () {
      expect(GroqCleanup.buildPrompt('Fix:', 'abc'), 'Fix:\n\nabc');
      expect(GroqCleanup.buildPrompt('', 'abc'), 'abc');
    });
  });

  group('DictationPipeline', () {
    DictationPipeline pipeline(String heard, {String? cleaned, bool cleanupFails = false, bool withCleanup = true}) {
      final stt = GroqSpeechToText(apiKey: 'k', client: MockClient((_) async => jsonResponse({'text': heard})));
      final cleanup = GroqCleanup(
          apiKey: 'k',
          client: MockClient((_) async => cleanupFails
              ? jsonResponse({'error': 'busy'}, 503)
              : jsonResponse({
                  'choices': [
                    {'message': {'content': cleaned ?? heard}}
                  ]
                })));
      return DictationPipeline(
          stt: stt,
          sttOptions: const SttOptions(model: 'whisper-large-v3'),
          cleanup: withCleanup ? cleanup : null,
          cleanupOptions: const CleanupOptions(model: 'm', promptTemplate: r'${output}'));
    }

    test('silence is not sent', () async {
      var called = false;
      final p = DictationPipeline(
          stt: GroqSpeechToText(apiKey: 'k', client: MockClient((_) async {
            called = true;
            return jsonResponse({'text': 'x'});
          })),
          sttOptions: const SttOptions(model: 'm'));
      final r = await p.process(Int16List(16000), 16000, DictationMode.raw);
      expect(r.outcome, DictationOutcome.silent);
      expect(called, isFalse);
    });

    test('raw mode returns what was heard', () async {
      final r = await pipeline('ei file e ekta login function banao').process(loudPcm(4), 16000, DictationMode.raw);
      expect(r.outcome, DictationOutcome.ok);
      expect(r.text, 'ei file e ekta login function banao');
    });

    test('hallucination is dropped', () async {
      final r = await pipeline('Thank you for watching.').process(loudPcm(4), 16000, DictationMode.raw);
      expect(r.outcome, DictationOutcome.hallucination);
    });

    test('clean mode uses cleanup, falls back to raw on failure or no key', () async {
      final ok = await pipeline('ekta login function banao', cleaned: 'Create a login function.')
          .process(loudPcm(4), 16000, DictationMode.clean);
      expect(ok.text, 'Create a login function.');
      final failed = await pipeline('ekta login function banao', cleanupFails: true)
          .process(loudPcm(4), 16000, DictationMode.clean);
      expect(failed.outcome, DictationOutcome.ok);
      expect(failed.text, 'ekta login function banao');
      final noKey = await pipeline('ekta login function banao', withCleanup: false)
          .process(loudPcm(4), 16000, DictationMode.clean);
      expect(noKey.text, 'ekta login function banao');
      expect(noKey.log.join('\n'), contains('Cleanup skipped'));
    });

    test('STT error is reported, not thrown', () async {
      final p = DictationPipeline(
          stt: GroqSpeechToText(apiKey: 'k', client: MockClient((_) async => jsonResponse({}, 429))),
          sttOptions: const SttOptions(model: 'm'));
      final r = await p.process(loudPcm(4), 16000, DictationMode.raw);
      expect(r.outcome, DictationOutcome.error);
      expect(r.error!.kind, ErrorKind.rateLimited);
    });
  });
}
