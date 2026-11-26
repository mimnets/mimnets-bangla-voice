import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:mimnets_bangla_voice/core/settings.dart';
import 'package:mimnets_bangla_voice/platform/hotkeys.dart';

void main() {
  test('parses the default hotkeys', () {
    final d = parseHotKey('ctrl+alt+d')!;
    expect(d.physicalKey, PhysicalKeyboardKey.keyD);
    expect(d.modifiers, [HotKeyModifier.control, HotKeyModifier.alt]);
    expect(d.scope, HotKeyScope.system);
    expect(parseHotKey('Ctrl + Shift + Space')!.physicalKey, PhysicalKeyboardKey.space);
    expect(parseHotKey('win+alt+f9')!.modifiers, [HotKeyModifier.meta, HotKeyModifier.alt]);
  });

  test('rejects bad hotkeys', () {
    expect(parseHotKey('d'), isNull); // no modifier
    expect(parseHotKey('ctrl+ctrl+d'), isNull);
    expect(parseHotKey('ctrl+banana'), isNull);
    expect(parseHotKey('hyper+d'), isNull);
    expect(parseHotKey(''), isNull);
  });

  test('describe', () {
    expect(describeHotKey('ctrl+alt+d'), 'Ctrl+Alt+D');
    expect(describeHotKey('ctrl+shift+space'), 'Ctrl+Shift+Space');
  });

  test('old default vocabulary hint is upgraded, custom one kept', () {
    final old = AppSettings.fromJson({
      'stt.prompt': 'Mixed Bangla and English speech about programming and AI tools. '
          'Words like VS Code, Python, JavaScript, React, function, API, file, folder, Claude, ChatGPT.'
    });
    expect(old.sttPrompt, AppSettings.defaultSttPrompt);
    expect(AppSettings.fromJson({'stt.prompt': 'my words'}).sttPrompt, 'my words');
  });
}
