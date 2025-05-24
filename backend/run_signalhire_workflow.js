const { spawn } = require('child_process');
const ngrok = require('ngrok');
const path = require('path');

async function run() {
  // 1. Start the callback server
  const callbackServer = spawn('node', [path.join(__dirname, 'signalhire_callback_server.js')], {
    stdio: 'inherit'
  });

  // 2. Start ngrok and get the public URL
  const url = await ngrok.connect({ addr: 3001, proto: 'http' });
  console.log('ngrok public URL:', url);
  const callbackUrl = url + '/callback';

  // 3. Run the main fetch script with the callback URL in the environment
  const fetchScript = spawn('node', [path.join(__dirname, 'fetch_ceo_info.js')], {
    stdio: 'inherit',
    env: { ...process.env, SIGNALHIRE_CALLBACK_URL: callbackUrl }
  });

  fetchScript.on('close', (code) => {
    console.log(`fetch_ceo_info.js exited with code ${code}`);
    // Optionally, kill the callback server and ngrok here
    callbackServer.kill();
    ngrok.disconnect();
    ngrok.kill();
    process.exit(code);
  });
}

run(); 