// PDFly API client — C# / .NET 6+
// Usage: dotnet script csharp_client.cs a.pdf b.pdf   (or a small console project)
using System.Net.Http;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

const string BASE = "http://localhost:5000";

async Task<JsonElement> Upload(string[] paths)
{
    using var http = new HttpClient();
    using var form = new MultipartFormDataContent();
    foreach (var p in paths)
        form.Add(new ByteArrayContent(File.ReadAllBytes(p)), "files", Path.GetFileName(p));
    var res = await http.PostAsync($"{BASE}/api/upload", form);
    return JsonDocument.Parse(await res.Content.ReadAsStringAsync()).RootElement;
}

async Task<JsonElement> Process(string jobId, string tool, Dictionary<string, object>? options = null)
{
    using var http = new HttpClient();
    var body = JsonSerializer.Serialize(new { job_id = jobId, tool, options = options ?? new() });
    var res = await http.PostAsync($"{BASE}/api/process",
        new StringContent(body, Encoding.UTF8, "application/json"));
    return JsonDocument.Parse(await res.Content.ReadAsStringAsync()).RootElement;
}

// ---- example: merge two PDFs ------------------------------------------
var up  = await Upload(args);
var res = await Process(up.GetProperty("job_id").GetString()!, "merge_pdf");
using (var http = new HttpClient())
{
    foreach (var f in res.GetProperty("files").EnumerateArray())
    {
        var url   = f.GetProperty("url").GetString()!;
        var name  = f.GetProperty("name").GetString()!;
        var bytes = await http.GetByteArrayAsync(BASE + url);
        File.WriteAllBytes(name, bytes);
        Console.WriteLine($"saved: {name} ({bytes.Length} bytes)");
    }
}
