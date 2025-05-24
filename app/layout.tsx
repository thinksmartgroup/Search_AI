import "./globals.css";
import React from "react";

export const metadata = {
  title: "ISV AI Platform",
  description: "Intelligent ISV search and enrichment system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Server-side logging only
  if (typeof window === 'undefined') {
    // eslint-disable-next-line no-console
    console.log('[RootLayout][SSR] Rendering on server. Children:', children);
    if (children) {
      // eslint-disable-next-line no-console
      console.log('[RootLayout][SSR] Children type:', typeof children);
      // eslint-disable-next-line no-console
      console.log('[RootLayout][SSR] Children keys:', Object.keys(children));
    }
  }

  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
