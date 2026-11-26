import 'package:hotkey_manager/hotkey_manager.dart';
import 'package:material_ui/material_ui.dart';

import 'ui/home_page.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Reclaim hotkeys left registered by a previous run or a hot restart.
  await hotKeyManager.unregisterAll();
  runApp(const BanglaVoiceApp());
}

class BanglaVoiceApp extends StatelessWidget {
  const BanglaVoiceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Mimnets Bangla Voice',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: const HomePage(),
    );
  }
}
