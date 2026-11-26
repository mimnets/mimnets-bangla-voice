import 'package:flutter_test/flutter_test.dart';
import 'package:mimnets_bangla_voice/core/filters.dart';

void main() {
  const long = Duration(seconds: 5);
  const short = Duration(seconds: 2);

  group('silence', () {
    test('below 400 is silent', () {
      expect(isSilent(0), isTrue);
      expect(isSilent(399), isTrue);
      expect(isSilent(400), isFalse);
    });
  });

  group('hallucination', () {
    test('known subtitle phrases are dropped', () {
      expect(isHallucination('Thank you for watching!', long), isTrue);
      expect(isHallucination('Please subscribe.', long), isTrue);
      expect(isHallucination('Subtitles by the Amara.org community', long), isTrue);
    });

    test('phrase inside a long real sentence is kept', () {
      expect(
          isHallucination(
              'In this file please add a login function and then subscribe to the auth state changes in React', long),
          isFalse);
    });

    test('short fillers only dropped when recording is short', () {
      expect(isHallucination('Thank you.', short), isTrue);
      expect(isHallucination('Thank you.', long), isFalse);
      expect(isHallucination('ধন্যবাদ।', short), isTrue);
      expect(isHallucination('...', short), isTrue);
    });

    test('real Bangla and mixed speech kept', () {
      expect(isHallucination('ei file e ekta login function banao', long), isFalse);
      expect(isHallucination('এই ফাইলে একটা লগইন ফাংশন বানাও', long), isFalse);
      expect(isHallucination('ঠিক আছে', short), isFalse);
    });
  });

  group('stripThinking', () {
    test('removes think blocks and quotes', () {
      expect(stripThinking('<think>hmm\nlet me see</think>\n"Add a login function."'), 'Add a login function.');
      expect(stripThinking('<THINK>x</THINK>Done'), 'Done');
      expect(stripThinking('plain'), 'plain');
    });
  });
}
