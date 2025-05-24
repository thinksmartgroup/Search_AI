import { NextResponse } from 'next/server';
import { GoogleGenerativeAI, HarmBlockThreshold, HarmCategory } from '@google/generative-ai';

const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const SERPAPI_KEY = process.env.SERPAPI_API_KEY;

const SYSTEM_PROMPT = `You are ISV-AI, an intelligent ISV research and enrichment assistant developed by Indraneel Bhattacharjee. 
- If you know the answer, answer directly.
- If you need to search the web, output SEARCH("your query") on a single line by itself. Do not answer until you have the search results.
- When you receive search results, use them to answer the user's question in detail.
- Do not hallucinate. If you cannot find the answer, say so.
- Do not output anything except the answer or SEARCH("...") as instructed.`;

type MessageRole = 'user' | 'model';
type Message = { role: MessageRole; parts: { text: string }[] };
type HistoryItem = { role: string; text: string };

async function callGemini(messages: Message[]) {
  const genAI = new GoogleGenerativeAI(GEMINI_API_KEY!);
  const model = genAI.getGenerativeModel({ model: 'gemini-2.5-pro-preview-03-25' });
  const result = await model.generateContent({
    contents: messages,
    generationConfig: { temperature: 0.7 },
    safetySettings: [
      { category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE },
      { category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE },
    ],
  });
  return result.response.text();
}

async function searchSerpApi(query: string) {
  if (!SERPAPI_KEY) throw new Error('SerpAPI key is missing');
  const serpApiUrl = `https://serpapi.com/search.json?q=${encodeURIComponent(query)}&engine=google&api_key=${SERPAPI_KEY}`;
  const serpRes = await fetch(serpApiUrl);
  if (!serpRes.ok) throw new Error('Failed to fetch from SerpAPI');
  const serpData = await serpRes.json();
  // Extract top 5 organic results
  const results = (serpData.organic_results || [])
    .filter((r: any) => r.link && r.title)
    .slice(0, 5)
    .map((r: any) => `- ${r.title} (${r.link})`)
    .join('\n');
  return results || 'No relevant results found.';
}

export async function POST(request: Request) {
  try {
    const { history } = await request.json();
    if (!history || !Array.isArray(history)) {
      return NextResponse.json({ error: 'History is required' }, { status: 400 });
    }
    if (!GEMINI_API_KEY) {
      return NextResponse.json({ error: 'Gemini API key is missing' }, { status: 500 });
    }
    // Reconstruct full messages array: system prompt + all user/model turns
    const messages: Message[] = [
      { role: 'model', parts: [{ text: SYSTEM_PROMPT }] },
      ...history.map((msg: HistoryItem) => ({
        role: (msg.role === 'system' ? 'model' : (msg.role === 'user' ? 'user' : 'model')) as MessageRole,
        parts: [{ text: msg.text }]
      })),
    ];
    let geminiResponse = await callGemini(messages);
    // If Gemini wants to search, do it
    const searchMatch = geminiResponse.match(/SEARCH\(["'](.+?)["']\)/i);
    if (searchMatch) {
      const searchQuery = searchMatch[1];
      const searchResults = await searchSerpApi(searchQuery);
      messages.push({ role: 'model', parts: [{ text: geminiResponse }] });
      messages.push({ role: 'user', parts: [{ text: `Here are the search results:\n${searchResults}` }] });
      geminiResponse = await callGemini(messages);
    }
    return NextResponse.json({ response: geminiResponse });
  } catch (error) {
    console.error('Error in Gemini agent chat:', error);
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Failed to chat with Gemini agent' }, { status: 500 });
  }
} 