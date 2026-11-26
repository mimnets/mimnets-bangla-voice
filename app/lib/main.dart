import 'package:material_ui/material_ui.dart';

import 'ui/home_page.dart';

void main() {
  runApp(const BanglaVoiceApp());
}

class BanglaVoiceApp extends StatelessWidget {
  const BanglaVoiceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Bangla Voice',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: Colors.teal, useMaterial3: true),
      home: const HomePage(),
    );
  }
}
