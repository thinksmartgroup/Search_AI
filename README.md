# ISV-AI Gemini Agent

A modern, full-stack AI-powered ISV (Independent Software Vendor) search and enrichment platform. Powered by Google Gemini 2.5 Pro, with intelligent tool use (web search, enrichment) and a beautiful Next.js chat UI.

---

## 🚀 Quickstart

### 1. **Clone the repository**
```
git clone <your-repo-url>
cd <project-root>
```

### 2. **Install dependencies**
```
npm install
```

### 3. **Set up environment variables**
Create a `.env` file in the project root with:
```
GEMINI_API_KEY=your_google_gemini_api_key
SERPAPI_API_KEY=your_serpapi_key
```

### 4. **Run the development server**
```
npm run dev
```

- The app will be available at [http://localhost:3000](http://localhost:3000) (or the next available port).

---

## 🧠 Features
- Conversational AI powered by Gemini 2.5 Pro
- Gemini agent can answer directly or trigger web search (via SerpAPI)
- Full multi-turn context retention
- Beautiful, modern chat UI with markdown/rich text support
- Easy to extend with more tools (e.g., enrichment APIs)

---

## 🛠️ Tech Stack
- Next.js 15 (App Router)
- Tailwind CSS
- Google Generative AI SDK
- SerpAPI
- React Markdown

---

## 📄 License
MIT
