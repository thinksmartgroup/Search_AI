import { NextResponse } from 'next/server';
import { writeFile } from 'fs/promises';
import { join } from 'path';

// Store responses in memory (in production, use a database)
let responses: any[] = [];

export async function POST(request: Request) {
  try {
    const data = await request.json();
    
    // Store the response
    responses.push(data);
    
    // Also save to a file for backup
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `signalhire_response_${timestamp}.json`;
    await writeFile(join(process.cwd(), 'data', filename), JSON.stringify(data, null, 2));
    
    return NextResponse.json({ status: 'success' });
  } catch (error) {
    console.error('Error processing callback:', error);
    return NextResponse.json(
      { status: 'error', message: 'Failed to process callback' },
      { status: 500 }
    );
  }
}

export async function GET() {
  // Return all stored responses
  return NextResponse.json(responses);
} 