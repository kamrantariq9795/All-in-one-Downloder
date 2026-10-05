import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: Color(0xFF04060B),
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const OmniDownloaderApp());
}

class OmniDownloaderApp extends StatelessWidget {
  const OmniDownloaderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'OmniDownloader PRO',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF070913),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6366F1),
          secondary: Color(0xFFA855F7),
          surface: Color(0xFF0B1021),
        ),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
