# PDFly API client — Ruby
# Usage: ruby ruby_client.rb a.pdf b.pdf
# gem install httparty
require 'httparty'

BASE = 'http://localhost:5000'

def pdfly_upload(paths)
  HTTParty.post("#{BASE}/api/upload",
                body: { files: paths.map { |p| File.open(p, 'rb') } }).parsed_response
end

def pdfly_process(job_id, tool, options = {})
  HTTParty.post("#{BASE}/api/process",
                body: { job_id: job_id, tool: tool, options: options }.to_json,
                headers: { 'Content-Type' => 'application/json' }).parsed_response
end

# ---- example: merge two PDFs ------------------------------------------
up   = pdfly_upload(ARGV)
res  = pdfly_process(up['job_id'], 'merge_pdf')
res['files'].each do |f|
  File.binwrite(f['name'], HTTParty.get(BASE + f['url']).body)
  puts "saved: #{f['name']} (#{f['size']} bytes)"
end
