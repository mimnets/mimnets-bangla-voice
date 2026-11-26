import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:mimnets_bangla_voice/platform/recorder.dart';
import 'package:mimnets_bangla_voice/platform/storage.dart';

void main() {
  test('secrets never reach the log', () {
    expect(redactSecrets('key gsk_abcdefgh12345678 used'), 'key gsk_*** used');
    expect(redactSecrets('sk-or-v1-abcdefghijkl'), 'sk-***');
    expect(redactSecrets('Authorization: Bearer abc.def'), 'Authorization: Bearer ***');
    expect(redactSecrets('Heard: ami bhalo achi'), 'Heard: ami bhalo achi');
  });

  test('measured rate', () {
    final r = Recording(Int16List(48000), 16000, const Duration(seconds: 3));
    expect(r.measuredRate, 16000);
    final wrong = Recording(Int16List(144000), 16000, const Duration(seconds: 3));
    expect(wrong.measuredRate, 48000);
  });
}
