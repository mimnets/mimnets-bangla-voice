import 'package:flutter/services.dart';
import 'package:hotkey_manager/hotkey_manager.dart';

/// Parses settings strings like "ctrl+alt+d" or "ctrl+shift+space" into a system-wide HotKey.
/// Returns null if the text isn't a valid combination.
HotKey? parseHotKey(String text) {
  final parts = text.toLowerCase().replaceAll(' ', '').split('+').where((p) => p.isNotEmpty).toList();
  if (parts.length < 2) return null; // need at least one modifier: plain keys would block typing
  final modifiers = <HotKeyModifier>[];
  for (final m in parts.sublist(0, parts.length - 1)) {
    final mod = switch (m) {
      'ctrl' || 'control' => HotKeyModifier.control,
      'alt' => HotKeyModifier.alt,
      'shift' => HotKeyModifier.shift,
      'win' || 'meta' || 'super' => HotKeyModifier.meta,
      _ => null,
    };
    if (mod == null || modifiers.contains(mod)) return null;
    modifiers.add(mod);
  }
  final key = _keys[parts.last];
  if (key == null) return null;
  return HotKey(key: key, modifiers: modifiers, scope: HotKeyScope.system);
}

/// "ctrl+alt+d" -> "Ctrl+Alt+D", for messages.
String describeHotKey(String text) => text
    .split('+')
    .map((p) => p.trim())
    .where((p) => p.isNotEmpty)
    .map((p) => p.length == 1 ? p.toUpperCase() : p[0].toUpperCase() + p.substring(1).toLowerCase())
    .join('+');

final Map<String, PhysicalKeyboardKey> _keys = {
  'a': PhysicalKeyboardKey.keyA, 'b': PhysicalKeyboardKey.keyB, 'c': PhysicalKeyboardKey.keyC,
  'd': PhysicalKeyboardKey.keyD, 'e': PhysicalKeyboardKey.keyE, 'f': PhysicalKeyboardKey.keyF,
  'g': PhysicalKeyboardKey.keyG, 'h': PhysicalKeyboardKey.keyH, 'i': PhysicalKeyboardKey.keyI,
  'j': PhysicalKeyboardKey.keyJ, 'k': PhysicalKeyboardKey.keyK, 'l': PhysicalKeyboardKey.keyL,
  'm': PhysicalKeyboardKey.keyM, 'n': PhysicalKeyboardKey.keyN, 'o': PhysicalKeyboardKey.keyO,
  'p': PhysicalKeyboardKey.keyP, 'q': PhysicalKeyboardKey.keyQ, 'r': PhysicalKeyboardKey.keyR,
  's': PhysicalKeyboardKey.keyS, 't': PhysicalKeyboardKey.keyT, 'u': PhysicalKeyboardKey.keyU,
  'v': PhysicalKeyboardKey.keyV, 'w': PhysicalKeyboardKey.keyW, 'x': PhysicalKeyboardKey.keyX,
  'y': PhysicalKeyboardKey.keyY, 'z': PhysicalKeyboardKey.keyZ,
  '0': PhysicalKeyboardKey.digit0, '1': PhysicalKeyboardKey.digit1, '2': PhysicalKeyboardKey.digit2,
  '3': PhysicalKeyboardKey.digit3, '4': PhysicalKeyboardKey.digit4, '5': PhysicalKeyboardKey.digit5,
  '6': PhysicalKeyboardKey.digit6, '7': PhysicalKeyboardKey.digit7, '8': PhysicalKeyboardKey.digit8,
  '9': PhysicalKeyboardKey.digit9,
  'f1': PhysicalKeyboardKey.f1, 'f2': PhysicalKeyboardKey.f2, 'f3': PhysicalKeyboardKey.f3,
  'f4': PhysicalKeyboardKey.f4, 'f5': PhysicalKeyboardKey.f5, 'f6': PhysicalKeyboardKey.f6,
  'f7': PhysicalKeyboardKey.f7, 'f8': PhysicalKeyboardKey.f8, 'f9': PhysicalKeyboardKey.f9,
  'f10': PhysicalKeyboardKey.f10, 'f11': PhysicalKeyboardKey.f11, 'f12': PhysicalKeyboardKey.f12,
  'space': PhysicalKeyboardKey.space,
};

/// Registers the two dictation hotkeys. Reports a plain message when Windows or another
/// app (e.g. Avro) already owns a combination.
class DictationHotkeys {
  final _registered = <HotKey>[];

  /// Returns one log line per hotkey.
  Future<List<String>> register({
    required String raw,
    required String clean,
    required void Function() onRaw,
    required void Function() onClean,
  }) async {
    await unregisterAll();
    final out = <String>[];
    for (final (text, label, handler) in [(raw, 'type exactly', onRaw), (clean, 'clean up', onClean)]) {
      final hk = parseHotKey(text);
      if (hk == null) {
        out.add('Hotkey "$text" is not valid. Use something like ctrl+alt+d.');
        continue;
      }
      try {
        await hotKeyManager.register(hk, keyDownHandler: (_) => handler());
        _registered.add(hk);
        out.add('Hotkey ${describeHotKey(text)} = $label');
      } on PlatformException catch (e) {
        out.add('Hotkey ${describeHotKey(text)} is taken by Windows or another app (${e.code}). '
            'Pick another one in Settings.');
      }
    }
    return out;
  }

  Future<void> unregisterAll() async {
    await hotKeyManager.unregisterAll();
    _registered.clear();
  }
}
