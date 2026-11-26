import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/settings.dart';

/// API keys in the OS secure store (never in settings JSON, files or the log).
class KeyStore {
  static const groq = 'groq_api_key';
  static const openRouter = 'openrouter_api_key';
  static const sarvam = 'sarvam_api_key';
  static const modalTokenId = 'modal_token_id';
  static const modalTokenSecret = 'modal_token_secret';

  final FlutterSecureStorage _s = const FlutterSecureStorage();

  Future<String> read(String name) async => (await _s.read(key: name)) ?? '';

  Future<void> write(String name, String value) =>
      value.trim().isEmpty ? _s.delete(key: name) : _s.write(key: name, value: value.trim());
}

/// Non-secret settings as one JSON string in shared_preferences.
class SettingsStore {
  static const _key = 'settings.v1';

  Future<AppSettings> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(_key);
    if (raw == null) return AppSettings();
    try {
      return AppSettings.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) {
      return AppSettings(); // corrupted file: start from defaults rather than crash
    }
  }

  Future<void> save(AppSettings s) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, jsonEncode(s.toJson()));
  }
}

/// Hides anything that looks like a key before it reaches the log.
String redactSecrets(String s) => s
    .replaceAll(RegExp(r'gsk_[A-Za-z0-9]{8,}'), 'gsk_***')
    .replaceAll(RegExp(r'sk-[A-Za-z0-9_\-]{8,}'), 'sk-***')
    .replaceAllMapped(RegExp(r'(Bearer\s+)\S+'), (m) => '${m[1]}***');
