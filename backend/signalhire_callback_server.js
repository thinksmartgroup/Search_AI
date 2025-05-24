const express = require('express');
const app = express();
app.use(express.json());

app.post('/callback', (req, res) => {
  console.log('\n========== SIGNALHIRE CALLBACK RECEIVED ==========');
  if (Array.isArray(req.body)) {
    req.body.forEach((result, idx) => {
      if (result.status === 'success' && result.candidate) {
        const c = result.candidate;
        const email = (c.contacts || []).find(x => x.type === 'email')?.value || 'N/A';
        const phone = (c.contacts || []).find(x => x.type === 'phone')?.value || 'N/A';
        console.log(`Result #${idx + 1}`);
        console.log('Name:', c.fullName || 'N/A');
        console.log('Title:', c.headLine || 'N/A');
        console.log('Email:', email);
        console.log('Phone:', phone);
        console.log('Company:', c.experience?.[0]?.company || 'N/A');
        console.log('---------------------------------------------');
      } else if (result.status === 'failed') {
        console.log(`Result #${idx + 1}: Candidate not found for item "${result.item}"`);
      } else {
        console.log(`Result #${idx + 1}:`, result.status, result.item);
      }
    });
  } else {
    console.log('Raw callback:', JSON.stringify(req.body, null, 2));
  }
  console.log('==================================================\n');
  res.status(200).send('OK');
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Callback server listening on port ${PORT}`);
}); 