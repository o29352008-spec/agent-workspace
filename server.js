const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const PORT = 8090;
const HOST = '0.0.0.0';
const STATIC_DIR = __dirname;

// OpenClaw CLI to fetch sessions
function getOpenClawSessions() {
  try {
    const raw = execSync('openclaw sessions --all-agents --active 1440 --json 2>/dev/null', {
      encoding: 'utf8',
      timeout: 5000,
    });
    const data = JSON.parse(raw);
    return data.sessions || [];
  } catch (e) {
    return null;
  }
}

// Session history — not available via CLI, return empty for now
function getSessionHistory(sessionKey, limit = 10) {
  // CLI doesn't expose history directly; future: use gateway websocket
  return { messages: [] };
}

const MIME_TYPES = {
  '.html': 'text/html',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

const server = http.createServer((req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');

  // API routes
  if (req.url === '/api/sessions') {
    const sessions = getOpenClawSessions();
    if (sessions) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(sessions));
    } else {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Could not fetch sessions' }));
    }
    return;
  }

  if (req.url.startsWith('/api/history/')) {
    const sessionKey = decodeURIComponent(req.url.replace('/api/history/', ''));
    const history = getSessionHistory(sessionKey);
    if (history) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(history));
    } else {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Could not fetch history' }));
    }
    return;
  }

  // Static files
  let filePath = req.url === '/' ? '/index.html' : req.url;
  filePath = path.join(STATIC_DIR, filePath);

  const ext = path.extname(filePath);
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404);
      res.end('Not found');
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`Agent Workspace server running at http://${HOST}:${PORT}`);
  console.log(`Polling OpenClaw sessions every 5s`);
});
