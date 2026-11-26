// Silence and hallucination filters, ported from prototype/dictate-python/app.py.

/// Recordings whose loudest sample is below this are not sent (about -38 dBFS).
const int silencePeakThreshold = 400;

bool isSilent(int peak) => peak < silencePeakThreshold;

/// Things Whisper "hears" in silence or noise (it learned them from video subtitles).
const List<String> hallucinationPhrases = [
  'thank you for watching',
  'thanks for watching',
  'please subscribe',
  'like and subscribe',
  'subscribe to',
  'subtitles by',
  'amara.org',
  'see you in the next video',
  'see you next time',
];

/// Dropped only when the recording is shorter than 3 seconds.
const Set<String> shortFillers = {'thank you', 'thanks', 'you', 'bye', 'okay', 'ধন্যবাদ'};

// Keep letters, combining marks (Bangla vowel signs and hasant), digits, spaces and dots.
// The prototype used Python's \w, which drops Bangla vowel signs, so "ধন্যবাদ" never matched.
final RegExp _junk = RegExp(r'[^\p{L}\p{M}\p{N}_\s.]', unicode: true);
final RegExp _spaces = RegExp(r'\s+');
final RegExp _edgeDotsSpaces = RegExp(r'^[\s.]+|[\s.]+$');

String _normalise(String text) =>
    text.toLowerCase().replaceAll(_junk, ' ').replaceAll(_spaces, ' ').trim();

/// True if [text] is probably invented by Whisper rather than spoken.
bool isHallucination(String text, Duration audioLength) {
  final t = _normalise(text);
  final words = t.isEmpty ? 0 : t.split(' ').length;
  if (words <= 10 && hallucinationPhrases.any(t.contains)) return true;
  if (audioLength < const Duration(seconds: 3)) {
    final core = t.replaceAll(_edgeDotsSpaces, '');
    if (core.isEmpty || shortFillers.contains(core)) return true;
  }
  return false;
}

final RegExp _think = RegExp(r'<think>.*?</think>', dotAll: true, caseSensitive: false);
final RegExp _edgeQuotes = RegExp(r'^"+|"+$');

/// Removes `<think>...</think>` blocks and surrounding quotes from an LLM reply.
String stripThinking(String s) =>
    s.replaceAll(_think, '').trim().replaceAll(_edgeQuotes, '').trim();
