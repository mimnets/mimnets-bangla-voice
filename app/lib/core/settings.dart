/// Non-secret app settings (stored as JSON). API keys are NOT here: they live in
/// secure storage. Defaults match prototype/dictate-python/app.py and Phase 1 results.
/// See docs/ARCHITECTURE.md section 3.
class AppSettings {
  static const int currentSchema = 1;

  /// Whisper copies the spelling style of this hint, so it includes colloquial Bangladeshi
  /// Bangla (তুমি, পাচ্ছো: words Whisper misspelled for the owner on 2026-11-27).
  static const defaultSttPrompt = 'Mixed Bangla and English speech about programming and AI tools. '
      'Words like VS Code, Python, JavaScript, React, function, API, file, '
      'folder, Claude, ChatGPT. তুমি কি শুনতে পাচ্ছো? আমি এই ফাইলে একটা login function বানাতে চাই।';

  /// Earlier defaults: saved settings that still hold one of these get the new default.
  static const _oldSttPrompts = {
    'Mixed Bangla and English speech about programming and AI tools. '
        'Words like VS Code, Python, JavaScript, React, function, API, file, '
        'folder, Claude, ChatGPT.',
  };

  static const defaultCleanupPrompt = 'You are cleaning up voice dictation. The speaker talks in Bangla, '
      'English, or a mix.\nFix transcription mistakes, then rewrite it as a '
      'clear English instruction.\nKeep code terms, file names, and technical '
      'words exactly as spoken.\nOutput only the final text, nothing else.\n\n'
      r'${output}';

  // speech to text
  String sttProvider = 'groq';
  String sttModel = 'whisper-large-v3';
  String sttLanguage = 'bn'; // 'bn' (default: auto-detect sometimes guesses Spanish etc.), 'en', '' = auto
  String sttPrompt = defaultSttPrompt;

  // cleanup
  String cleanupProvider = 'groq';
  String cleanupModel = 'openai/gpt-oss-120b';
  String cleanupPrompt = defaultCleanupPrompt;

  // hotkeys
  String hotkeyRaw = 'ctrl+alt+d';
  String hotkeyClean = 'ctrl+alt+e';

  // audio, paste, window
  String? inputDevice; // null = system default
  bool beep = true;
  String pasteMethod = 'clipboard'; // or 'type'
  bool onTop = false;
  bool startWithWindows = false;

  // voice clone (Phase 1 winner: BanglaBox, cfg_weight 0.8)
  String cloneBackend = 'manual-colab'; // or 'banglabox-modal'
  String cloneServerUrl = '';
  double cloneCfgWeight = 0.8;
  double cloneExaggeration = 0.5;
  double cloneTemperature = 0.5;
  int cloneSeed = 0;
  double clonePauseSeconds = 0.25;

  AppSettings();

  /// Reads saved JSON. Missing or wrongly typed fields keep their defaults, so old or
  /// hand-edited files never crash the app.
  factory AppSettings.fromJson(Map<String, dynamic> j) {
    final s = AppSettings();
    T pick<T>(String key, T fallback) {
      final v = j[key];
      if (v is T) return v;
      if (fallback is double && v is num) return v.toDouble() as T;
      return fallback;
    }

    s.sttProvider = pick('stt.provider', s.sttProvider);
    s.sttModel = pick('stt.model', s.sttModel);
    s.sttLanguage = pick('stt.language', s.sttLanguage);
    s.sttPrompt = pick('stt.prompt', s.sttPrompt);
    if (_oldSttPrompts.contains(s.sttPrompt)) s.sttPrompt = defaultSttPrompt;
    s.cleanupProvider = pick('cleanup.provider', s.cleanupProvider);
    s.cleanupModel = pick('cleanup.model', s.cleanupModel);
    s.cleanupPrompt = pick('cleanup.prompt', s.cleanupPrompt);
    s.hotkeyRaw = pick('hotkeys.raw', s.hotkeyRaw);
    s.hotkeyClean = pick('hotkeys.clean', s.hotkeyClean);
    s.inputDevice = j['audio.inputDevice'] is String ? j['audio.inputDevice'] as String : null;
    s.beep = pick('audio.beep', s.beep);
    s.pasteMethod = pick('paste.method', s.pasteMethod);
    s.onTop = pick('window.onTop', s.onTop);
    s.startWithWindows = pick('app.startWithWindows', s.startWithWindows);
    s.cloneBackend = pick('clone.backend', s.cloneBackend);
    s.cloneServerUrl = pick('clone.serverUrl', s.cloneServerUrl);
    s.cloneCfgWeight = pick('clone.cfgWeight', s.cloneCfgWeight);
    s.cloneExaggeration = pick('clone.exaggeration', s.cloneExaggeration);
    s.cloneTemperature = pick('clone.temperature', s.cloneTemperature);
    s.cloneSeed = pick('clone.seed', s.cloneSeed);
    s.clonePauseSeconds = pick('clone.pauseSeconds', s.clonePauseSeconds);
    // Future: migrate older schemaVersion values here.
    return s;
  }

  Map<String, dynamic> toJson() => {
        'schemaVersion': currentSchema,
        'stt.provider': sttProvider,
        'stt.model': sttModel,
        'stt.language': sttLanguage,
        'stt.prompt': sttPrompt,
        'cleanup.provider': cleanupProvider,
        'cleanup.model': cleanupModel,
        'cleanup.prompt': cleanupPrompt,
        'hotkeys.raw': hotkeyRaw,
        'hotkeys.clean': hotkeyClean,
        'audio.inputDevice': inputDevice,
        'audio.beep': beep,
        'paste.method': pasteMethod,
        'window.onTop': onTop,
        'app.startWithWindows': startWithWindows,
        'clone.backend': cloneBackend,
        'clone.serverUrl': cloneServerUrl,
        'clone.cfgWeight': cloneCfgWeight,
        'clone.exaggeration': cloneExaggeration,
        'clone.temperature': cloneTemperature,
        'clone.seed': cloneSeed,
        'clone.pauseSeconds': clonePauseSeconds,
      };
}
