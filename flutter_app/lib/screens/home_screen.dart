import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:fluttertoast/fluttertoast.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // Change to your PC/Server IP address
  String serverBaseUrl = "http://192.168.0.101:5000";

  final TextEditingController _urlController = TextEditingController();
  bool _isLoading = false;
  Map<String, dynamic>? _videoData;

  String _selectedQuality = "best";
  String _selectedFormat = "video"; // 'video' or 'audio'

  // Download tracking state
  bool _isDownloading = false;
  double _downloadProgress = 0.0;
  String _downloadSpeed = "0 MB/s";
  String _downloadStatusText = "Downloading...";
  Timer? _pollTimer;

  @override
  void dispose() {
    _urlController.dispose();
    _pollTimer?.cancel();
    super.dispose();
  }

  void _toast(String msg) {
    Fluttertoast.showToast(
      msg: msg,
      toastLength: Toast.LENGTH_SHORT,
      gravity: ToastGravity.BOTTOM,
      backgroundColor: const Color(0xFF1E295D),
      textColor: Colors.white,
    );
  }

  // Paste from clipboard
  Future<void> _pasteFromClipboard() async {
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    if (data != null && data.text != null && data.text!.isNotEmpty) {
      setState(() {
        _urlController.text = data.text!;
      });
      _toast("Link pasted!");
      _fetchVideoInfo();
    } else {
      _toast("Clipboard is empty.");
    }
  }

  // Fetch video metadata from server
  Future<void> _fetchVideoInfo() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) {
      _toast("Please enter or paste a video link.");
      return;
    }

    setState(() {
      _isLoading = true;
      _videoData = null;
    });

    try {
      final res = await http.post(
        Uri.parse('$serverBaseUrl/api/info'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'url': url}),
      ).timeout(const Duration(seconds: 15));

      final data = jsonDecode(res.body);
      if (data['success'] == true) {
        setState(() {
          _videoData = data;
          _selectedQuality = "best";
          _selectedFormat = "video";
        });
      } else {
        _toast(data['error'] ?? 'Failed to fetch video information.');
      }
    } catch (e) {
      _toast("Connection error: $e");
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  // Request Android storage permissions
  Future<bool> _requestStoragePermission() async {
    if (Platform.isAndroid) {
      if (await Permission.storage.request().isGranted) {
        return true;
      }
      if (await Permission.manageExternalStorage.request().isGranted) {
        return true;
      }
      return true; // Android 13+ handles public downloads without legacy permission
    }
    return true;
  }

  // Start Download
  Future<void> _startDownload() async {
    if (_videoData == null) return;

    final url = _videoData!['url'];
    setState(() {
      _isDownloading = true;
      _downloadProgress = 0.05;
      _downloadStatusText = "Initiating server extraction...";
    });

    try {
      final res = await http.post(
        Uri.parse('$serverBaseUrl/api/download'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'url': url,
          'quality': _selectedQuality,
          'format': _selectedFormat,
          'title': _videoData!['title'],
        }),
      );

      final data = jsonDecode(res.body);
      if (data['success'] == true && data['task_id'] != null) {
        _pollTaskProgress(data['task_id']);
      } else {
        _toast(data['error'] ?? "Failed to start download");
        setState(() => _isDownloading = false);
      }
    } catch (e) {
      _toast("Download error: $e");
      setState(() => _isDownloading = false);
    }
  }

  // Poll server progress and then download file to Android device
  void _pollTaskProgress(String taskId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 800), (timer) async {
      try {
        final res = await http.get(Uri.parse('$serverBaseUrl/api/progress/$taskId'));
        final data = jsonDecode(res.body);
        if (data['success'] == true && data['task'] != null) {
          final t = data['task'];
          final status = t['status'];
          final progress = (t['progress'] as num?)?.toDouble() ?? 0.0;
          final speed = t['speed'] ?? "0 MB/s";
          final filename = t['filename'];

          setState(() {
            _downloadProgress = (progress / 100.0).clamp(0.05, 1.0);
            _downloadSpeed = speed;
            if (status == 'downloading') {
              _downloadStatusText = "Downloading stream ($speed)...";
            } else if (status == 'processing') {
              _downloadStatusText = "Merging Video & Audio (FFmpeg)...";
            }
          });

          if (status == 'finished') {
            timer.cancel();
            setState(() {
              _downloadProgress = 1.0;
              _downloadStatusText = "Saving to mobile Downloads folder...";
            });

            // Save to Mobile Device
            if (filename != null) {
              await _saveFileToMobile(filename);
            }
          } else if (status == 'error') {
            timer.cancel();
            setState(() => _isDownloading = false);
            _toast("Download error: ${t['error']}");
          }
        }
      } catch (e) {
        // Continue polling
      }
    });
  }

  // Download directly into Android's Downloads directory
  Future<void> _saveFileToMobile(String filename) async {
    try {
      await _requestStoragePermission();

      Directory? downloadDir;
      if (Platform.isAndroid) {
        downloadDir = Directory('/storage/emulated/0/Download');
        if (!await downloadDir.exists()) {
          downloadDir = await getExternalStorageDirectory();
        }
      } else {
        downloadDir = await getApplicationDocumentsDirectory();
      }

      final savePath = '${downloadDir!.path}/$filename';
      final downloadUrl = '$serverBaseUrl/api/file/${Uri.encodeComponent(filename)}?attachment=true';

      final dio = Dio();
      await dio.download(downloadUrl, savePath);

      _toast("Saved to phone: $filename");
      setState(() {
        _isDownloading = false;
        _downloadStatusText = "Download Complete!";
      });
    } catch (e) {
      _toast("Saved on server. Mobile save note: $e");
      setState(() => _isDownloading = false);
    }
  }

  // Settings dialog to edit server IP
  void _openSettingsDialog() {
    final ipController = TextEditingController(text: serverBaseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0D1127),
        title: const Text("Server Settings", style: TextStyle(color: Colors.white, fontSize: 16)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              "Apne PC ka local IP address enter karein (e.g., http://192.168.0.101:5000):",
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: ipController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFF141B3D),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Cancel"),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                serverBaseUrl = ipController.text.trim();
              });
              Navigator.pop(ctx);
              _toast("Server IP updated!");
            },
            child: const Text("Save"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF070913),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF6366F1), Color(0xFFA855F7), Color(0xFFEC4899)],
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.cloud_download, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 8),
            const Text(
              "OmniDownloader",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
            ),
            const SizedBox(width: 5),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981).withOpacity(0.2),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.4)),
              ),
              child: const Text("PRO", style: TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings, color: Colors.white70, size: 20),
            onPressed: _openSettingsDialog,
            tooltip: "Server IP",
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Subtitle
            const Center(
              child: Text(
                "All Platforms • 100% No Watermark • 4K & MP3",
                style: TextStyle(color: Colors.white54, fontSize: 11),
              ),
            ),
            const SizedBox(height: 14),

            // Input Card
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF0D1127),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withOpacity(0.08)),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _urlController,
                          style: const TextStyle(color: Colors.white, fontSize: 13),
                          decoration: InputDecoration(
                            hintText: "Paste video link here...",
                            hintStyle: const TextStyle(color: Colors.white38, fontSize: 12),
                            prefixIcon: const Icon(Icons.link, color: Colors.white38, size: 18),
                            filled: true,
                            fillColor: const Color(0xFF070913),
                            contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: const BorderSide(color: Color(0xFF6366F1)),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: _pasteFromClipboard,
                        style: ElevatedButton.styleKey: null,
                        child: const Text("Paste", style: TextStyle(fontSize: 12)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    height: 44,
                    child: ElevatedButton.icon(
                      onPressed: _isLoading ? null : _fetchVideoInfo,
                      icon: _isLoading
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                          : const Icon(Icons.search, size: 18),
                      label: Text(_isLoading ? "Fetching Stream..." : "Fetch Video"),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4F46E5),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Video Preview Card
            if (_videoData != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1127),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF6366F1).withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Thumbnail
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Stack(
                        alignment: Alignment.bottomLeft,
                        children: [
                          AspectRatio(
                            aspectRatio: 16 / 9,
                            child: _videoData!['thumbnail'] != null && _videoData!['thumbnail'].toString().isNotEmpty
                                ? Image.network(
                                    '$serverBaseUrl/api/thumbnail?url=${Uri.encodeComponent(_videoData!['thumbnail'])}',
                                    fit: BoxFit.cover,
                                    errorBuilder: (ctx, err, stack) => Container(
                                      color: const Color(0xFF141B3D),
                                      child: const Icon(Icons.movie, color: Colors.white38, size: 40),
                                    ),
                                  )
                                : Container(color: const Color(0xFF141B3D)),
                          ),
                          Container(
                            padding: const EdgeInsets.all(6),
                            child: Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF10B981),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: const Text("NO WATERMARK", style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.bold)),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Title
                    Text(
                      _videoData!['title'] ?? 'Video',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 12),

                    // Format Toggle
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => setState(() => _selectedFormat = "video"),
                            icon: const Icon(Icons.video_file, size: 16),
                            label: const Text("Video (MP4)", style: TextStyle(fontSize: 11)),
                            style: OutlinedButton.styleFrom(
                              backgroundColor: _selectedFormat == "video" ? const Color(0xFF6366F1).withOpacity(0.2) : Colors.transparent,
                              side: BorderSide(color: _selectedFormat == "video" ? const Color(0xFF6366F1) : Colors.white24),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => setState(() {
                              _selectedFormat = "audio";
                              _selectedQuality = "mp3";
                            }),
                            icon: const Icon(Icons.music_note, size: 16),
                            label: const Text("Audio (MP3)", style: TextStyle(fontSize: 11)),
                            style: OutlinedButton.styleFrom(
                              backgroundColor: _selectedFormat == "audio" ? const Color(0xFF6366F1).withOpacity(0.2) : Colors.transparent,
                              side: BorderSide(color: _selectedFormat == "audio" ? const Color(0xFF6366F1) : Colors.white24),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // Download Action Button
                    SizedBox(
                      width: double.infinity,
                      height: 46,
                      child: ElevatedButton.icon(
                        onPressed: _isDownloading ? null : _startDownload,
                        icon: const Icon(Icons.file_download, color: Color(0xFF070913)),
                        label: Text(
                          _selectedFormat == "video" ? "Download Video (No Watermark)" : "Download MP3 Audio (HQ)",
                          style: const TextStyle(color: Color(0xFF070913), fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Progress Card
            if (_isDownloading) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0D1127),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: const Color(0xFF10B981).withOpacity(0.4)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(_downloadStatusText, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
                        Text("${(_downloadProgress * 100).toInt()}%", style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.bold)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: _downloadProgress,
                      backgroundColor: const Color(0xFF141B3D),
                      color: const Color(0xFF10B981),
                      minHeight: 6,
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
