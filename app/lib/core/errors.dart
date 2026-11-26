/// One error type for every cloud call, with a plain-language message for the UI.
/// See docs/ARCHITECTURE.md section 5.
enum ErrorKind {
  badRequest,
  badKey,
  needsCredit,
  tooLarge,
  notFound,
  rateLimited,
  serverBusy,
  offline,
  timeout,
  unknown,
}

class ProviderError implements Exception {
  ProviderError(this.kind, {required this.service, this.status, this.detail = '', this.retryAfter});

  final ErrorKind kind;
  final String service; // "Groq", "OpenRouter", "Voice server"
  final int? status;
  final String detail; // first 300 chars of the response body, for the log
  final Duration? retryAfter;

  /// Builds an error from a non-2xx HTTP response.
  factory ProviderError.fromResponse(String service, int status, String body,
      [Map<String, String> headers = const {}]) {
    final kind = switch (status) {
      400 || 422 => ErrorKind.badRequest,
      401 || 403 => ErrorKind.badKey,
      402 => ErrorKind.needsCredit,
      404 => ErrorKind.notFound,
      413 => ErrorKind.tooLarge,
      429 => ErrorKind.rateLimited,
      498 || 500 || 502 || 503 || 504 => ErrorKind.serverBusy,
      _ => ErrorKind.unknown,
    };
    final seconds = double.tryParse(headers['retry-after'] ?? '');
    return ProviderError(kind,
        service: service,
        status: status,
        detail: body.length > 300 ? body.substring(0, 300) : body,
        retryAfter: seconds == null ? null : Duration(milliseconds: (seconds * 1000).round()));
  }

  /// True for errors worth one automatic retry.
  bool get isTransient => kind == ErrorKind.serverBusy;

  String get userMessage => switch (kind) {
        ErrorKind.badKey => service == 'Voice server'
            ? 'Voice server token is wrong. Check Settings.'
            : '$service API key is wrong or expired. Check Settings.',
        ErrorKind.needsCredit => '$service needs credit for this. Switch back to Groq (free).',
        ErrorKind.rateLimited => retryAfter == null
            ? 'Free limit reached for now. Wait a minute and try again.'
            : 'Free limit reached. Try again in ${retryAfter!.inSeconds + 1} s.',
        ErrorKind.serverBusy => '$service is busy. Try again in a moment.',
        ErrorKind.offline => 'No internet connection.',
        ErrorKind.timeout => '$service took too long to answer. Try again.',
        ErrorKind.tooLarge => 'The recording is too long for $service.',
        ErrorKind.notFound => '$service could not find what was asked for.',
        ErrorKind.badRequest => '$service rejected the request. See the log.',
        ErrorKind.unknown => '$service error${status == null ? '' : ' ($status)'}. See the log.',
      };

  @override
  String toString() => '$service error ${status ?? kind.name}: $detail';
}
