require('dotenv').config({ path: '.env' });
require('dotenv').config({ path: '.env.local', override: true });

const fs = require('fs').promises;
const fsSync = require('fs');
const path = require('path');
const https = require('https');
const { google } = require('googleapis');

const SIGNALHIRE_API_KEY = process.env.SG_HIRE;
const SIGNALHIRE_BASE_URL = 'https://www.signalhire.com/api/v1/candidate/search';
const RANGE = 'Vendors!A:A';
const GOOGLE_CREDENTIALS_FILE = process.env.GOOGLE_CREDENTIALS_FILE || 'credentials.json';
const CALLBACK_URL = process.env.SIGNALHIRE_CALLBACK_URL || 'https://your-ngrok-url.ngrok.io/callback';

const SHEET_URLS = {
  optometry: process.env.OPTOMETRY_SHEET_URL,
  chiropractic: process.env.CHIRO_SHEET_URL,
  auto_repair: process.env.AUTO_REPAIR_SHEET_URL,
};

console.log('GOOGLE_CREDENTIALS_FILE:', GOOGLE_CREDENTIALS_FILE);
console.log('SG_HIRE:', SIGNALHIRE_API_KEY ? 'set' : 'NOT SET');
console.log('Sheet URLs:', SHEET_URLS);
console.log('CALLBACK_URL:', CALLBACK_URL);

if (!fsSync.existsSync(GOOGLE_CREDENTIALS_FILE)) {
  console.error(`Error: Google credentials file "${GOOGLE_CREDENTIALS_FILE}" not found.`);
  process.exit(1);
}

if (CALLBACK_URL === 'https://your-ngrok-url.ngrok.io/callback') {
  console.warn('WARNING: Using placeholder callbackUrl. Set SIGNALHIRE_CALLBACK_URL in your .env to a real, accessible URL!');
}

function extractSheetId(url) {
  if (!url) return null;
  const match = url.match(/\/d\/([a-zA-Z0-9-_]+)/);
  return match ? match[1] : null;
}

async function getGoogleSheetsClient() {
  const auth = new google.auth.GoogleAuth({
    keyFile: GOOGLE_CREDENTIALS_FILE,
    scopes: ['https://www.googleapis.com/auth/spreadsheets.readonly'],
  });
  return google.sheets({ version: 'v4', auth });
}

async function getWebsitesFromSheet(spreadsheetId) {
  try {
    const sheets = await getGoogleSheetsClient();
    const response = await sheets.spreadsheets.values.get({
      spreadsheetId,
      range: RANGE,
    });
    const rows = response.data.values;
    if (!rows || rows.length === 0) {
      console.log('No data found in sheet.');
      return [];
    }
    // Filter out empty rows and header if exists
    return rows
      .flat()
      .filter(url => url && url.trim() !== '' && url !== 'Website')
      .map(url => url.trim());
  } catch (error) {
    console.error('Error reading from Google Sheets:', error);
    throw error;
  }
}

async function makeRequest(options, data) {
  return new Promise((resolve, reject) => {
    const req = https.request(options, (res) => {
      let responseData = '';
      res.on('data', (chunk) => {
        responseData += chunk;
      });
      res.on('end', () => {
        try {
          resolve(JSON.parse(responseData));
        } catch (e) {
          resolve(responseData);
        }
      });
    });
    req.on('error', (error) => {
      reject(error);
    });
    if (data) {
      req.write(JSON.stringify(data));
    }
    req.end();
  });
}

async function searchSignalHire(website) {
  const options = {
    hostname: 'www.signalhire.com',
    path: '/api/v1/candidate/search',
    method: 'POST',
    headers: {
      'apikey': SIGNALHIRE_API_KEY,
      'Content-Type': 'application/json'
    }
  };
  const searchData = {
    items: [website],
    callbackUrl: CALLBACK_URL
  };
  try {
    const response = await makeRequest(options, searchData);
    if (response && response.requestId) {
      console.log(`Search initiated for "${website}": requestId = ${response.requestId}`);
      console.log('Waiting for callback with results for this requestId...');
    } else {
      console.log('Unexpected response from SignalHire:', response);
    }
    return response;
  } catch (error) {
    console.error('Error searching SignalHire:', error);
    throw error;
  }
}

async function processResults(results, website, industry) {
  if (!results || !results.candidate) {
    console.log('No candidate data found');
    return;
  }
  const candidate = results.candidate;
  const contacts = candidate.contacts || [];
  const email = contacts.find(c => c.type === 'email')?.value || 'N/A';
  const phone = contacts.find(c => c.type === 'phone')?.value || 'N/A';
  const ceoInfo = {
    industry,
    website,
    name: candidate.fullName || 'N/A',
    title: candidate.headLine || 'N/A',
    email,
    phone
  };
  console.log(`\n[${industry.toUpperCase()}] CEO Information:`);
  console.log('----------------');
  console.log(`Website: ${website}`);
  console.log(`Name: ${ceoInfo.name}`);
  console.log(`Title: ${ceoInfo.title}`);
  console.log(`Email: ${ceoInfo.email}`);
  console.log(`Phone: ${ceoInfo.phone}`);
  // Save to file
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `ceo_info_${industry}_${timestamp}.json`;
  await fs.writeFile(
    path.join('data', filename),
    JSON.stringify(ceoInfo, null, 2)
  );
  console.log(`\nResults saved to: ${filename}`);
}

async function main() {
  if (!SIGNALHIRE_API_KEY) {
    console.error('Error: SG_HIRE environment variable is not set');
    process.exit(1);
  }
  try {
    for (const [industry, url] of Object.entries(SHEET_URLS)) {
      if (!url) {
        console.log(`No URL set for ${industry}`);
        continue;
      }
      const spreadsheetId = extractSheetId(url);
      if (!spreadsheetId) {
        console.log(`Could not extract sheet ID for ${industry}`);
        continue;
      }
      console.log(`\nFetching websites from ${industry} sheet...`);
      const websites = await getWebsitesFromSheet(spreadsheetId);
      console.log(`Found ${websites.length} websites to process in ${industry}`);
      for (const website of websites) {
        console.log(`\nProcessing website: ${website}`);
        try {
          const results = await searchSignalHire(website);
          await processResults(results, website, industry);
          await new Promise(resolve => setTimeout(resolve, 1000));
        } catch (error) {
          console.error(`Error processing ${website}:`, error.message);
          continue;
        }
      }
    }
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

main(); 