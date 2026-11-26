import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import '../errors.dart';
import '../filters.dart';
import 'providers.dart';

const groqBaseUrl = 'https://api.groq.com/openai/v1';

/// Runs an HTTP call and turns network failures and timeouts into [ProviderError].
Future<http.Response> sendGuarded(String service, Duration timeout, Future<http.Response> Function() call) async {
  try {
    return await call().timeout(timeout);
  } on TimeoutException {
    throw ProviderError(ErrorKind.timeout, service: service);
  } on SocketException catch (e) {
    throw ProviderError(ErrorKind.offline, service: service, detail: e.message);
  } on http.ClientException catch (e) {
    throw ProviderError(ErrorKind.offline, service: service, detail: e.message);
  }
}

/// Decodes a JSON body as UTF-8 (http's `body` getter would mangle Bangla without a charset).
Map<String, dynamic> decodeJson(http.Response r) => jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;

/// Groq Whisper: POST /audio/transcriptions (multipart).
class GroqSpeechToText implements SpeechToText {
  GroqSpeechToText({required this.apiKey, http.Client? client, this.baseUrl = groqBaseUrl})
      : _client = client ?? http.Client();

  final String apiKey;
  final String baseUrl;
  final http.Client _client;

  @override
  String get id => 'groq';

  @override
  Future<Transcript> transcribe(Uint8List wav, SttOptions o) async {
    final r = await sendGuarded('Groq', const Duration(seconds: 60), () async {
      final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/audio/transcriptions'))
        ..headers['Authorization'] = 'Bearer $apiKey'
        ..fields['model'] = o.model
        ..fields['temperature'] = '0'
        ..fields['response_format'] = 'json'
        ..files.add(http.MultipartFile.fromBytes('file', wav,
            filename: 'audio.wav', contentType: MediaType('audio', 'wav')));
      if ((o.language ?? '').isNotEmpty) req.fields['language'] = o.language!;
      if ((o.prompt ?? '').isNotEmpty) req.fields['prompt'] = o.prompt!;
      return http.Response.fromStream(await _client.send(req));
    });
    if (r.statusCode != 200) {
      throw ProviderError.fromResponse('Groq', r.statusCode, utf8.decode(r.bodyBytes, allowMalformed: true), r.headers);
    }
    return Transcript(((decodeJson(r)['text'] as String?) ?? '').trim(), o.model);
  }
}

/// Groq chat (OpenAI-compatible) used to clean dictation into an English instruction.
class GroqCleanup implements TextCleanup {
  GroqCleanup({required this.apiKey, http.Client? client, this.baseUrl = groqBaseUrl})
      : _client = client ?? http.Client();

  final String apiKey;
  final String baseUrl;
  final http.Client _client;

  @override
  String get id => 'groq';

  static String buildPrompt(String template, String text) {
    final tpl = template.isEmpty ? r'${output}' : template;
    return tpl.contains(r'${output}') ? tpl.replaceAll(r'${output}', text) : '$tpl\n\n$text';
  }

  @override
  Future<String> clean(String text, CleanupOptions o) async {
    final payload = <String, dynamic>{
      'model': o.model,
      'messages': [
        {'role': 'user', 'content': buildPrompt(o.promptTemplate, text)}
      ],
      'temperature': 0.2,
      'reasoning_effort': 'low',
    };
    Future<http.Response> post() => sendGuarded(
        'Groq',
        const Duration(seconds: 30),
        () => _client.post(Uri.parse('$baseUrl/chat/completions'),
            headers: {'Authorization': 'Bearer $apiKey', 'Content-Type': 'application/json'},
            body: jsonEncode(payload)));

    var r = await post();
    if (r.statusCode == 400 && utf8.decode(r.bodyBytes, allowMalformed: true).contains('reasoning')) {
      payload.remove('reasoning_effort'); // model doesn't support it: retry without
      r = await post();
    }
    if (r.statusCode != 200) {
      throw ProviderError.fromResponse('Groq', r.statusCode, utf8.decode(r.bodyBytes, allowMalformed: true), r.headers);
    }
    final content = (((decodeJson(r)['choices'] as List).first as Map)['message'] as Map)['content'] as String? ?? '';
    final cleaned = stripThinking(content);
    return cleaned.isEmpty ? text : cleaned;
  }
}
