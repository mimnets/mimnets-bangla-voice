import 'dart:ffi';

import 'package:ffi/ffi.dart';
import 'package:flutter/services.dart';
import 'package:win32/win32.dart';

/// Puts text into whatever app has focus (Windows). See docs/ARCHITECTURE.md section 7.
///
/// clipboard (default, the prototype's way): save clipboard -> copy text -> wait until
/// Ctrl/Alt/Shift/Win are released -> Ctrl+V -> restore the old clipboard after 0.4 s.
///
/// type: sends the text as Unicode key presses and never touches the clipboard.
/// For apps that block paste; slower for long text.
class PasteService {
  static const _vkV = 0x56;

  static bool _isDown(VIRTUAL_KEY vk) => (GetAsyncKeyState(vk) & 0x8000) != 0;

  /// The hotkey's own Ctrl+Alt must be up, or Ctrl+V becomes Ctrl+Alt+V.
  Future<void> waitForModifiersRelease({Duration timeout = const Duration(seconds: 2)}) async {
    final end = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(end)) {
      if (![VK_CONTROL, VK_MENU, VK_SHIFT, VK_LWIN, VK_RWIN].any(_isDown)) return;
      await Future<void>.delayed(const Duration(milliseconds: 30));
    }
  }

  /// Sends key events: each entry is (virtual key, scan code, flags).
  void _send(List<(int, int, int)> events) {
    final inputs = calloc<INPUT>(events.length);
    try {
      for (var i = 0; i < events.length; i++) {
        final (vk, scan, flags) = events[i];
        final input = (inputs + i).ref;
        input.type = INPUT_KEYBOARD;
        input.Anonymous.ki.wVk = VIRTUAL_KEY(vk);
        input.Anonymous.ki.wScan = scan;
        input.Anonymous.ki.dwFlags = KEYBD_EVENT_FLAGS(flags);
      }
      SendInput(events.length, inputs, sizeOf<INPUT>());
    } finally {
      calloc.free(inputs);
    }
  }

  Future<void> pasteViaClipboard(String text) async {
    String? old;
    try {
      old = (await Clipboard.getData(Clipboard.kTextPlain))?.text;
    } catch (_) {
      old = null; // clipboard busy or holds non-text: just don't restore
    }
    await Clipboard.setData(ClipboardData(text: text));
    await waitForModifiersRelease();
    await Future<void>.delayed(const Duration(milliseconds: 50));
    final up = KEYEVENTF_KEYUP as int;
    _send([(VK_CONTROL as int, 0, 0), (_vkV, 0, 0), (_vkV, 0, up), (VK_CONTROL as int, 0, up)]);
    if (old != null) {
      await Future<void>.delayed(const Duration(milliseconds: 400));
      await Clipboard.setData(ClipboardData(text: old));
    }
  }

  Future<void> typeText(String text) async {
    await waitForModifiersRelease();
    await Future<void>.delayed(const Duration(milliseconds: 50));
    final uni = KEYEVENTF_UNICODE as int;
    final up = KEYEVENTF_KEYUP as int;
    final units = text.replaceAll('\r\n', '\n').replaceAll('\n', '\r').codeUnits; // Enter = CR
    for (var i = 0; i < units.length; i += 50) {
      final batch = units.sublist(i, i + 50 > units.length ? units.length : i + 50);
      _send([for (final u in batch) ...[(0, u, uni), (0, u, uni | up)]]);
      await Future<void>.delayed(const Duration(milliseconds: 10));
    }
  }

  Future<void> insert(String text, {required String method}) =>
      method == 'type' ? typeText(text) : pasteViaClipboard(text);
}
