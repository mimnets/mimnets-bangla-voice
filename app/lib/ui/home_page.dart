import 'dart:async';
import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter/services.dart';
import 'package:record/record.dart' show InputDevice;

import '../core/dictation.dart';
import '../core/providers/groq.dart';
import '../core/providers/providers.dart';
import '../core/settings.dart';
import '../core/wav.dart';
import '../platform/recorder.dart';
import '../platform/storage.dart';

/// Main window: key setup, mic choice, Record, level meter, Test mic, result, log.
/// Same layout idea as the prototype. Hotkeys and paste come in Phase 3 step 3.
class HomePage extends StatefulWidget {
  const HomePage({super.key});
  @override
  State<HomePage> createState() => _HomePageState();
}

enum _Busy { idle, recording, testing, working }

class _HomePageState extends State<HomePage> {
  final _recorder = Recorder();
  final _keys = KeyStore();
  final _settingsStore = SettingsStore();
  final _player = AudioPlayer();
  final _keyCtrl = TextEditingController();
  final _resultCtrl = TextEditingController();
  final _logLines = <String>[];
  final _logScroll = ScrollController();

  AppSettings _settings = AppSettings();
  List<InputDevice> _devices = [];
  DictationMode _mode = DictationMode.raw;
  _Busy _busy = _Busy.idle;
  double _level = 0;
  String _status = 'Starting...';
  Color _statusColor = Colors.grey;
  StreamSubscription<double>? _levelSub;
  bool _keyHidden = true;

  @override
  void initState() {
    super.initState();
    _levelSub = _recorder.level.listen((v) => setState(() => _level = v));
    _init();
  }

  Future<void> _init() async {
    _settings = await _settingsStore.load();
    _keyCtrl.text = await _keys.read(KeyStore.groq);
    await _refreshDevices();
    _setStatus(_keyCtrl.text.isEmpty ? 'Paste your free Groq key, then Save.' : 'Ready. Click Record and speak.',
        Colors.black87);
  }

  Future<void> _refreshDevices() async {
    try {
      final d = await _recorder.devices();
      setState(() => _devices = d);
      _log('Microphones: ${d.isEmpty ? '(none found)' : d.map((e) => e.label).join(', ')}');
    } catch (e) {
      _log('Could not list microphones: $e');
    }
  }

  void _setStatus(String s, Color c) => setState(() {
        _status = s;
        _statusColor = c;
      });

  void _log(String line) {
    final t = TimeOfDay.now();
    setState(() => _logLines.add('${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}  '
        '${redactSecrets(line)}'));
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_logScroll.hasClients) _logScroll.jumpTo(_logScroll.position.maxScrollExtent);
    });
  }

  Future<void> _saveKey() async {
    await _keys.write(KeyStore.groq, _keyCtrl.text);
    await _settingsStore.save(_settings);
    _log('Key saved in Windows secure storage. Now click Record and speak.');
    _setStatus('Ready. Click Record and speak.', Colors.black87);
  }

  Future<void> _toggleRecord() async {
    if (_busy == _Busy.recording) {
      final rec = await _recorder.stop();
      setState(() => _busy = _Busy.working);
      _log('Recorded ${(rec.wallTime.inMilliseconds / 1000).toStringAsFixed(1)} s, '
          'peak ${peakAmplitude(rec.pcm)}, measured rate ~${rec.measuredRate} Hz');
      await _process(rec);
      return;
    }
    if (_busy != _Busy.idle) return;
    if (_keyCtrl.text.trim().isEmpty) {
      _setStatus('Paste your Groq key first, then Save.', Colors.red);
      return;
    }
    try {
      await _recorder.start(deviceId: _settings.inputDevice);
      setState(() => _busy = _Busy.recording);
      _setStatus('● Recording... click Stop when done', Colors.red);
    } on RecorderException catch (e) {
      _log('ERROR: $e');
      _setStatus('Mic error, see log', Colors.red);
    }
  }

  Future<void> _process(Recording rec) async {
    _setStatus(_mode == DictationMode.clean ? 'Transcribing and cleaning up...' : 'Transcribing...', Colors.orange);
    final key = _keyCtrl.text.trim();
    final pipeline = DictationPipeline(
      stt: GroqSpeechToText(apiKey: key),
      sttOptions: SttOptions(model: _settings.sttModel, language: _settings.sttLanguage, prompt: _settings.sttPrompt),
      cleanup: GroqCleanup(apiKey: key),
      cleanupOptions: CleanupOptions(model: _settings.cleanupModel, promptTemplate: _settings.cleanupPrompt),
    );
    final r = await pipeline.process(rec.pcm, rec.sampleRate, _mode);
    r.log.forEach(_log);
    switch (r.outcome) {
      case DictationOutcome.ok:
        _resultCtrl.text = r.text;
        _setStatus('✓ Done. Dictation works!', Colors.green);
      case DictationOutcome.silent:
        _setStatus('No voice heard. Check the mic.', Colors.red);
      case DictationOutcome.nothingHeard:
        _setStatus('Nothing recognised, try again.', Colors.red);
      case DictationOutcome.hallucination:
        _setStatus('No clear speech, try again.', Colors.red);
      case DictationOutcome.error:
        _setStatus(r.error!.userMessage, Colors.red);
    }
    setState(() => _busy = _Busy.idle);
  }

  Future<void> _testMic() async {
    if (_busy != _Busy.idle) return;
    setState(() => _busy = _Busy.testing);
    try {
      _setStatus('● Mic test: say something for 3 seconds', Colors.red);
      final rec = await _recorder.recordFor(const Duration(seconds: 3), deviceId: _settings.inputDevice);
      final peak = peakAmplitude(rec.pcm);
      _log('Mic test: peak level $peak, measured rate ~${rec.measuredRate} Hz '
          '(asked for ${rec.sampleRate} Hz)');
      if ((rec.measuredRate - rec.sampleRate).abs() > rec.sampleRate * 0.15) {
        _log('WARNING: the mic is not delivering ${rec.sampleRate} Hz. Tell Claude Code this number.');
      }
      if (peak < 300) {
        _setStatus('Mic test: almost silent. Pick another microphone.', Colors.red);
      } else {
        _setStatus('Playing it back...', Colors.orange);
        final f = File('${Directory.systemTemp.path}${Platform.pathSeparator}mimnets_mic_test.wav');
        await f.writeAsBytes(pcm16ToWav(rec.pcm, rec.sampleRate));
        await _player.play(DeviceFileSource(f.path));
        await _player.onPlayerComplete.first.timeout(const Duration(seconds: 6), onTimeout: () {});
        _setStatus('Mic test OK. Click Record and speak.', Colors.green);
      }
    } on RecorderException catch (e) {
      _log('ERROR: $e');
      _setStatus('Mic error, see log', Colors.red);
    } finally {
      setState(() => _busy = _Busy.idle);
    }
  }

  @override
  void dispose() {
    _levelSub?.cancel();
    _recorder.dispose();
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final recording = _busy == _Busy.recording;
    return Scaffold(
      appBar: AppBar(title: const Text('Mimnets Bangla Voice: dictation')),
      body: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(
              child: TextField(
                controller: _keyCtrl,
                obscureText: _keyHidden,
                decoration: InputDecoration(
                  labelText: 'Groq API key (free: console.groq.com/keys)',
                  border: const OutlineInputBorder(),
                  isDense: true,
                  suffixIcon: IconButton(
                      icon: Icon(_keyHidden ? Icons.visibility : Icons.visibility_off),
                      onPressed: () => setState(() => _keyHidden = !_keyHidden)),
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(onPressed: _saveKey, child: const Text('Save key')),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            const Text('Microphone: '),
            Expanded(
              child: DropdownButton<String?>(
                isExpanded: true,
                value: _devices.any((d) => d.id == _settings.inputDevice) ? _settings.inputDevice : null,
                items: [
                  const DropdownMenuItem<String?>(value: null, child: Text('Windows default')),
                  ..._devices.map((d) => DropdownMenuItem<String?>(value: d.id, child: Text(d.label))),
                ],
                onChanged: _busy == _Busy.idle
                    ? (v) {
                        setState(() => _settings.inputDevice = v);
                        _settingsStore.save(_settings);
                      }
                    : null,
              ),
            ),
            IconButton(tooltip: 'Refresh list', onPressed: _refreshDevices, icon: const Icon(Icons.refresh)),
          ]),
          Row(children: [
            const Text('Language: '),
            DropdownButton<String>(
              value: _settings.sttLanguage,
              items: const [
                DropdownMenuItem(value: 'bn', child: Text('Bangla (recommended)')),
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: '', child: Text('Auto detect (can guess wrong)')),
              ],
              onChanged: _busy == _Busy.idle
                  ? (v) {
                      setState(() => _settings.sttLanguage = v ?? 'bn');
                      _settingsStore.save(_settings);
                      _log('Language set to ${v!.isEmpty ? 'auto detect' : v}.');
                    }
                  : null,
            ),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            SegmentedButton<DictationMode>(
              segments: const [
                ButtonSegment(value: DictationMode.raw, label: Text('Type exactly what I say')),
                ButtonSegment(value: DictationMode.clean, label: Text('Clean up into English prompt')),
              ],
              selected: {_mode},
              onSelectionChanged: _busy == _Busy.idle ? (s) => setState(() => _mode = s.first) : null,
            ),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: recording ? Colors.red : null),
              onPressed: (_busy == _Busy.idle || recording) ? _toggleRecord : null,
              icon: Icon(recording ? Icons.stop : Icons.mic),
              label: Text(recording ? 'Stop' : 'Record'),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
                onPressed: _busy == _Busy.idle ? _testMic : null,
                icon: const Icon(Icons.hearing),
                label: const Text('Test mic')),
            const SizedBox(width: 12),
            Expanded(
              child: ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                    value: _level, minHeight: 14, color: _level > 0.97 ? Colors.red : Colors.green),
              ),
            ),
          ]),
          const SizedBox(height: 8),
          Text(_status, style: TextStyle(color: _statusColor, fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Row(children: [
            const Text('Result'),
            const Spacer(),
            TextButton.icon(
                onPressed: () => Clipboard.setData(ClipboardData(text: _resultCtrl.text)),
                icon: const Icon(Icons.copy, size: 16),
                label: const Text('Copy')),
          ]),
          SizedBox(
            height: 110,
            child: TextField(
                controller: _resultCtrl,
                maxLines: null,
                expands: true,
                style: const TextStyle(fontSize: 16),
                decoration: const InputDecoration(border: OutlineInputBorder())),
          ),
          const SizedBox(height: 8),
          const Text('Log'),
          Expanded(
            child: Container(
              decoration: BoxDecoration(border: Border.all(color: Colors.black26), borderRadius: BorderRadius.circular(4)),
              padding: const EdgeInsets.all(6),
              child: ListView.builder(
                controller: _logScroll,
                itemCount: _logLines.length,
                itemBuilder: (_, i) => SelectableText(_logLines[i], style: const TextStyle(fontSize: 12, fontFamily: 'Consolas')),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
