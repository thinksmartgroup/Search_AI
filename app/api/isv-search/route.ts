import { NextResponse } from 'next/server';

const SERPAPI_KEY = process.env.SERPAPI_API_KEY;

// Helper to normalize URLs for deduplication
function normalizeUrl(url: string): string {
  if (!url) return '';
  return url
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '');
}

// Simulated search and enrichment logic
async function enrichWithSignalHire(company: any) {
  try {
    await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || ''}/api/signalhire/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ website: company.website }),
    });
    const start = Date.now();
    let ceo = null;
    while (Date.now() - start < 15000) {
      const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || ''}/api/signalhire/callback`);
      const allResults = await res.json();
      const match = allResults.find((r: any) => {
        const candidate = r.candidate;
        if (!candidate) return false;
        return (
          (candidate.website && normalizeUrl(candidate.website) === normalizeUrl(company.website)) ||
          (candidate.company && company.name && candidate.company.toLowerCase().includes(company.name.toLowerCase()))
        );
      });
      if (match && match.candidate) {
        const candidate = match.candidate;
        const contacts = candidate.contacts || [];
        ceo = {
          name: candidate.fullName || 'N/A',
          title: candidate.headLine || 'N/A',
          email: contacts.find((c: any) => c.type === 'email')?.value || 'N/A',
          phone: contacts.find((c: any) => c.type === 'phone')?.value || 'N/A',
        };
        break;
      }
      await new Promise(res => setTimeout(res, 1500));
    }
    if (!ceo) {
      ceo = { name: 'Not found', title: '', email: '', phone: '' };
    }
    return { ...company, ceo };
  } catch (error) {
    console.error('SignalHire enrichment error:', error);
    return { ...company, ceo: { name: 'Error', title: '', email: '', phone: '' } };
  }
}

async function searchISVs(query: string) {
  if (!SERPAPI_KEY) {
    throw new Error('SerpAPI key is missing');
  }
  // Call SerpAPI Google Search API
  const serpApiUrl = `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google&api_key=${SERPAPI_KEY}`;
  const serpRes = await fetch(serpApiUrl);
  if (!serpRes.ok) {
    throw new Error('Failed to fetch from SerpAPI');
  }
  const serpData = await serpRes.json();
  // Extract top 3 organic results with a website
  const results = (serpData.organic_results || [])
    .filter((r: any) => r.link && r.title)
    .slice(0, 3)
    .map((r: any) => ({ name: r.title, website: r.link }));

  // Deduplicate by normalized website
  const seen = new Set<string>();
  const uniqueResults = results.filter((company: any) => {
    const norm = normalizeUrl(company.website);
    if (!norm || seen.has(norm)) return false;
    seen.add(norm);
    return true;
  });

  return uniqueResults;
}

export async function POST(request: Request) {
  try {
    const { query } = await request.json();
    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }
    const companies = await searchISVs(query);
    const enrichedResults = await Promise.all(companies.map(enrichWithSignalHire));
    return NextResponse.json({ results: enrichedResults });
  } catch (error) {
    console.error('Error in ISV search:', error);
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Failed to search ISVs' }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({ message: "ISV Search API is working!" });
} 