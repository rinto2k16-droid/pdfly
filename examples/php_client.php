<?php
/**
 * PDFly API client — PHP
 * Usage: php php_client.php a.pdf b.pdf
 *
 * Requires curl + json (bundled with PHP).
 */
function pdfly_upload(string $base, array $paths): array {
    $fields = [];
    foreach ($paths as $p) {
        $fields['files'][] = new CURLFile(realpath($p), mime_content_type($p), basename($p));
    }
    $ch = curl_init($base . '/api/upload');
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true,
                            CURLOPT_POSTFIELDS => $fields]);
    $res = json_decode(curl_exec($ch), true);
    curl_close($ch);
    if (!($res['ok'] ?? false)) throw new RuntimeException('Upload failed: ' . ($res['error'] ?? '?'));
    return $res;
}

function pdfly_process(string $base, string $jobId, string $tool, array $options = []): array {
    $ch = curl_init($base . '/api/process');
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => json_encode(['job_id' => $jobId, 'tool' => $tool, 'options' => $options])]);
    $res = json_decode(curl_exec($ch), true);
    curl_close($ch);
    if (!($res['ok'] ?? false)) throw new RuntimeException('Process failed: ' . ($res['error'] ?? '?'));
    return $res;
}

/* ---- example: merge two PDFs ---------------------------------------- */
$base = 'http://localhost:5000';
$up   = pdfly_upload($base, array_slice($argv, 1));            // e.g. a.pdf b.pdf
$res  = pdfly_process($base, $up['job_id'], 'merge_pdf');
foreach ($res['files'] as $f) {
    file_put_contents($f['name'], file_get_contents($base . $f['url']));
    echo "saved: {$f['name']} ({$f['size']} bytes)\n";
}
