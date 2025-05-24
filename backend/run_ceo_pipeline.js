const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const http = require('http');

function updateEnv(callbackUrl) {
  const envPath = path.join(__dirname, '.env');
  let env = fs.readFileSync(envPath, 'utf-8');
  if (env.match(/^SIGNALHIRE_CALLBACK_URL=.*$/m)) {
    env = env.replace(/^SIGNALHIRE_CALLBACK_URL=.*$/m, `SIGNALHIRE_CALLBACK_URL=${callbackUrl}`);
  } else {
    env += `\nSIGNALHIRE_CALLBACK_URL=${callbackUrl}\n`;
  }
  fs.writeFileSync(envPath, env, 'utf-8');
  console.log(`Updated .env with SIGNALHIRE_CALLBACK_URL=${callbackUrl}`);
}

function startCallbackServer() {
  const server = spawn('node', [path.join(__dirname, 'signalhire_callback_server.js')], {
    stdio: 'inherit'
  });
  return server;
}

function startNgrok() {
  return new Promise((resolve, reject) => {
    const ngrok = spawn('npx', ['ngrok', 'http', '3001', '--log=stdout']);
    let resolved = false;
    // Poll ngrok's local API for the public URL
    const start = Date.now();
    const poll = setInterval(() => {
      http.get('http://127.0.0.1:4040/api/tunnels', (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => {
          try {
            const tunnels = JSON.parse(data).tunnels;
            const tunnel = tunnels.find(t => t.public_url && t.public_url.startsWith('https://'));
            if (tunnel) {
              clearInterval(poll);
              resolved = true;
              resolve({ ngrok, url: tunnel.public_url });
            }
          } catch {}
        });
      }).on('error', () => {});
      if (Date.now() - start > 10000 && !resolved) {
        clearInterval(poll);
        reject(new Error('ngrok public URL not found after 10 seconds'));
      }
    }, 500);
    ngrok.stderr.on('data', (data) => {
      process.stderr.write(data);
    });
    ngrok.on('close', (code) => {
      if (!resolved) reject(new Error('ngrok failed to start'));
    });
  });
}

function runMainScript() {
  const main = spawn('node', [path.join(__dirname, 'fetch_ceo_info.js')], {
    stdio: 'inherit'
  });
  return main;
}

(async () => {
  // 1. Start callback server
  const callbackServer = startCallbackServer();

  // 2. Start ngrok and get public URL
  const { ngrok, url } = await startNgrok();
  const callbackUrl = url + '/callback';
  updateEnv(callbackUrl);

  // 3. Run main script
  const main = runMainScript();

  main.on('close', (code) => {
    console.log(`fetch_ceo_info.js exited with code ${code}`);
    callbackServer.kill();
    ngrok.kill();
    process.exit(code);
  });

  process.on('SIGINT', () => {
    callbackServer.kill();
    ngrok.kill();
    process.exit();
  });
})(); 