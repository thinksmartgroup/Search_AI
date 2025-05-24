import { NextResponse } from 'next/server';

const SIGNALHIRE_API_KEY = process.env.SG_HIRE;
const SIGNALHIRE_BASE_URL = 'https://www.signalhire.com/api/v1/candidate/search';

export async function POST(request: Request) {
  try {
    const { website } = await request.json();
    
    if (!website) {
      return NextResponse.json(
        { error: 'Website is required' },
        { status: 400 }
      );
    }

    const headers = {
      'apikey': SIGNALHIRE_API_KEY || '',
      'Content-Type': 'application/json'
    };

    const searchData = {
      items: [website],
      callbackUrl: `${process.env.NEXT_PUBLIC_BASE_URL}/api/signalhire/callback`
    };

    const response = await fetch(SIGNALHIRE_BASE_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(searchData)
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: `SignalHire API error: ${error}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error searching SignalHire:', error);
    return NextResponse.json(
      { error: 'Failed to search SignalHire' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({ message: "SignalHire Search API is working!" });
} 