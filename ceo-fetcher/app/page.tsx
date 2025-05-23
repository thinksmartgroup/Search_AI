'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface CEOInfo {
  name: string;
  title: string;
  email: string;
  phone: string;
}

export default function Home() {
  const [website, setWebsite] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [ceoInfo, setCeoInfo] = useState<CEOInfo | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setCeoInfo(null);

    try {
      const response = await fetch('/api/signalhire/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ website }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(error);
      }

      // Start polling for results
      const pollInterval = setInterval(async () => {
        const resultsResponse = await fetch('/api/signalhire/callback');
        const results = await resultsResponse.json();
        
        if (results && results.length > 0) {
          const latestResult = results[results.length - 1];
          if (latestResult.status === 'success' && latestResult.candidate) {
            const candidate = latestResult.candidate;
            const contacts = candidate.contacts || [];
            const email = contacts.find((c: any) => c.type === 'email')?.value || 'N/A';
            const phone = contacts.find((c: any) => c.type === 'phone')?.value || 'N/A';
            
            setCeoInfo({
              name: candidate.fullName || 'N/A',
              title: candidate.headLine || 'N/A',
              email,
              phone,
            });
            clearInterval(pollInterval);
            setLoading(false);
          }
        }
      }, 2000); // Poll every 2 seconds

      // Stop polling after 30 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        if (!ceoInfo) {
          setError('Timeout waiting for results');
          setLoading(false);
        }
      }, 30000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">CEO Information Fetcher</h1>
        
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="mb-4">
            <label htmlFor="website" className="block text-sm font-medium mb-2">
              Company Website
            </label>
            <input
              type="url"
              id="website"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
              placeholder="https://example.com"
              required
              className="w-full px-4 py-2 border rounded-md"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600 disabled:bg-gray-400"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {ceoInfo && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">CEO Information</h2>
            <dl className="space-y-2">
              <div>
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="mt-1">{ceoInfo.name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Title</dt>
                <dd className="mt-1">{ceoInfo.title}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Email</dt>
                <dd className="mt-1">{ceoInfo.email}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Phone</dt>
                <dd className="mt-1">{ceoInfo.phone}</dd>
              </div>
            </dl>
          </div>
        )}
      </div>
    </main>
  );
} 