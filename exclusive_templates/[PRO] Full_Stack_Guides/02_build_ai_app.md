# 🤖 Build an AI-Powered App — Complete Guide

> **Estimated market value: $79** (AI/ML courses on Udemy: $49-$149)
>
> Build a production AI application with OpenAI, RAG (Retrieval-Augmented Generation),
> streaming responses, function calling, and image generation.

---

## Table of Contents
1. [OpenAI Setup & Best Practices](#1-setup)
2. [Streaming Chat Interface](#2-streaming)
3. [RAG — Chat with Your Documents](#3-rag)
4. [Function Calling / Tool Use](#4-function-calling)
5. [Image Generation with DALL-E](#5-dalle)
6. [AI Agents Pattern](#6-agents)
7. [Rate Limiting & Cost Control](#7-costs)
8. [Production Deployment](#8-production)

---

## 1. OpenAI Setup & Best Practices

### Install Dependencies
```bash
npm install openai ai              # Vercel AI SDK + OpenAI
npm install @pinecone-database/pinecone  # Vector DB for RAG
npm install pdf-parse               # PDF parsing for documents
npm install tiktoken                # Token counting
```

### Client Setup
```typescript
// src/lib/openai.ts
import OpenAI from "openai"

export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
})

// Model selection guide:
// gpt-4o         — Best quality, $2.50/1M input tokens
// gpt-4o-mini    — Fast + cheap, $0.15/1M input tokens  
// gpt-3.5-turbo  — Legacy, cheapest
// o1             — Reasoning model for complex tasks
```

---

## 2. Streaming Chat Interface

### API Route with Streaming
```typescript
// src/app/api/chat/route.ts
import { openai } from "@/lib/openai"
import { OpenAIStream, StreamingTextResponse } from "ai"

export const runtime = "edge"

export async function POST(req: Request) {
  const { messages, model = "gpt-4o-mini" } = await req.json()

  const response = await openai.chat.completions.create({
    model,
    messages: [
      {
        role: "system",
        content: `You are a helpful AI assistant. Be concise and accurate.
                  Current date: ${new Date().toISOString().split("T")[0]}`,
      },
      ...messages,
    ],
    stream: true,
    temperature: 0.7,
    max_tokens: 2000,
  })

  const stream = OpenAIStream(response)
  return new StreamingTextResponse(stream)
}
```

### React Chat Component
```typescript
// src/components/chat.tsx
"use client"
import { useChat } from "ai/react"
import { useRef, useEffect } from "react"

export function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="flex flex-col h-[600px]">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : ""}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2 ${
              m.role === "user" 
                ? "bg-blue-600 text-white" 
                : "bg-gray-100 dark:bg-gray-800"
            }`}>
              <p className="whitespace-pre-wrap">{m.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-1">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
          </div>
        )}
        <div ref={scrollRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="border-t p-4 flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Type a message..."
          className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2"
        />
        <button 
          type="submit" 
          disabled={isLoading}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
```

---

## 3. RAG — Chat with Your Documents

### Document Processing Pipeline
```typescript
// src/lib/rag.ts
import { openai } from "./openai"
import { Pinecone } from "@pinecone-database/pinecone"

const pinecone = new Pinecone({ apiKey: process.env.PINECONE_API_KEY! })
const index = pinecone.index("documents")

// Step 1: Split document into chunks
export function chunkText(text: string, chunkSize = 500, overlap = 50): string[] {
  const chunks: string[] = []
  for (let i = 0; i < text.length; i += chunkSize - overlap) {
    chunks.push(text.slice(i, i + chunkSize))
  }
  return chunks
}

// Step 2: Generate embeddings
export async function generateEmbeddings(texts: string[]) {
  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",  // $0.02/1M tokens
    input: texts,
  })
  return response.data.map((d) => d.embedding)
}

// Step 3: Store in vector database
export async function storeDocumentChunks(
  documentId: string,
  chunks: string[]
) {
  const embeddings = await generateEmbeddings(chunks)
  
  const vectors = chunks.map((chunk, i) => ({
    id: `${documentId}_${i}`,
    values: embeddings[i],
    metadata: { text: chunk, documentId },
  }))

  await index.upsert(vectors)
}

// Step 4: Query with context
export async function queryWithContext(question: string, topK = 5) {
  const [queryEmbedding] = await generateEmbeddings([question])
  
  const results = await index.query({
    vector: queryEmbedding,
    topK,
    includeMetadata: true,
  })

  const context = results.matches
    .map((match) => match.metadata?.text)
    .join("\n\n")

  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      {
        role: "system",
        content: `Answer based on this context. If the answer isn't in the context, say so.
        
Context:
${context}`,
      },
      { role: "user", content: question },
    ],
  })

  return {
    answer: response.choices[0].message.content,
    sources: results.matches.map((m) => ({
      text: m.metadata?.text,
      score: m.score,
    })),
  }
}
```

---

## 4. Function Calling / Tool Use

```typescript
// src/lib/ai-tools.ts
import { openai } from "./openai"

const tools = [
  {
    type: "function" as const,
    function: {
      name: "get_weather",
      description: "Get the current weather for a location",
      parameters: {
        type: "object",
        properties: {
          location: { type: "string", description: "City name" },
          unit: { type: "string", enum: ["celsius", "fahrenheit"] },
        },
        required: ["location"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "search_products",
      description: "Search for products in the database",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string" },
          maxPrice: { type: "number" },
          category: { type: "string" },
        },
        required: ["query"],
      },
    },
  },
]

// Tool implementations
async function get_weather(args: { location: string; unit?: string }) {
  // In production, call a real weather API
  return { temp: 22, condition: "Sunny", location: args.location }
}

async function search_products(args: { query: string; maxPrice?: number }) {
  // In production, query your database
  return [
    { name: "Product A", price: 29.99 },
    { name: "Product B", price: 49.99 },
  ]
}

const toolMap: Record<string, Function> = { get_weather, search_products }

export async function chatWithTools(userMessage: string) {
  const messages: any[] = [
    { role: "system", content: "You are a helpful assistant with access to tools." },
    { role: "user", content: userMessage },
  ]

  // First call — may request tool use
  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages,
    tools,
    tool_choice: "auto",
  })

  const message = response.choices[0].message

  // If the model wants to call tools
  if (message.tool_calls) {
    messages.push(message)

    for (const toolCall of message.tool_calls) {
      const fn = toolMap[toolCall.function.name]
      const args = JSON.parse(toolCall.function.arguments)
      const result = await fn(args)

      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(result),
      })
    }

    // Second call — with tool results
    const finalResponse = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages,
    })

    return finalResponse.choices[0].message.content
  }

  return message.content
}
```

---

## 5. Image Generation with DALL-E

```typescript
// src/lib/image-gen.ts
import { openai } from "./openai"

export async function generateImage(prompt: string) {
  const response = await openai.images.generate({
    model: "dall-e-3",           // Best quality
    prompt,
    n: 1,
    size: "1024x1024",          // Options: 1024x1024, 1792x1024, 1024x1792
    quality: "standard",         // "standard" or "hd"
    style: "vivid",              // "vivid" or "natural"
  })

  return response.data[0].url
}

export async function editImage(imageBuffer: Buffer, prompt: string) {
  const response = await openai.images.edit({
    model: "dall-e-2",
    image: imageBuffer,
    prompt,
    n: 1,
    size: "1024x1024",
  })

  return response.data[0].url
}
```

---

## 6. AI Agents Pattern

```typescript
// src/lib/agent.ts
import { openai } from "./openai"

interface AgentStep {
  thought: string
  action: string
  result: string
}

export async function runAgent(task: string, maxSteps = 5) {
  const steps: AgentStep[] = []
  let currentTask = task

  for (let i = 0; i < maxSteps; i++) {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content: `You are an AI agent. For each step, respond in JSON:
{
  "thought": "what you're thinking",
  "action": "search|calculate|answer",
  "actionInput": "input for the action",
  "isFinal": true/false,
  "finalAnswer": "only if isFinal is true"
}`,
        },
        { role: "user", content: currentTask },
        ...steps.map((s) => ({
          role: "assistant" as const,
          content: `Thought: ${s.thought}\nAction: ${s.action}\nResult: ${s.result}`,
        })),
      ],
      response_format: { type: "json_object" },
    })

    const step = JSON.parse(response.choices[0].message.content!)

    if (step.isFinal) {
      return { answer: step.finalAnswer, steps }
    }

    // Execute action (simplified)
    const result = await executeAction(step.action, step.actionInput)
    steps.push({ thought: step.thought, action: step.action, result })
  }

  return { answer: "Max steps reached", steps }
}

async function executeAction(action: string, input: string): Promise<string> {
  switch (action) {
    case "search": return `Search results for: ${input}`
    case "calculate": return String(eval(input))
    default: return "Unknown action"
  }
}
```

---

## 7. Rate Limiting & Cost Control

```typescript
// src/lib/rate-limit.ts
const rateLimitMap = new Map<string, { count: number; resetTime: number }>()

export function rateLimit(userId: string, limit = 20, windowMs = 60000) {
  const now = Date.now()
  const userLimit = rateLimitMap.get(userId)

  if (!userLimit || now > userLimit.resetTime) {
    rateLimitMap.set(userId, { count: 1, resetTime: now + windowMs })
    return { allowed: true, remaining: limit - 1 }
  }

  if (userLimit.count >= limit) {
    return { allowed: false, remaining: 0, resetIn: userLimit.resetTime - now }
  }

  userLimit.count++
  return { allowed: true, remaining: limit - userLimit.count }
}

// Cost estimation
export function estimateCost(tokens: number, model: string) {
  const prices: Record<string, { input: number; output: number }> = {
    "gpt-4o":      { input: 2.50, output: 10.00 },  // per 1M tokens
    "gpt-4o-mini": { input: 0.15, output: 0.60 },
    "o1":          { input: 15.00, output: 60.00 },
  }
  const price = prices[model] || prices["gpt-4o-mini"]
  return (tokens / 1_000_000) * price.input
}
```

---

## 8. Production Deployment

### Cost Monitoring Setup
```typescript
// Track API usage per user
export async function trackUsage(userId: string, model: string, tokens: number) {
  await db.apiUsage.create({
    data: {
      userId,
      model,
      inputTokens: tokens,
      cost: estimateCost(tokens, model),
      timestamp: new Date(),
    },
  })
}
```

### Monthly Budget Alerts
```typescript
export async function checkBudget(userId: string, monthlyLimit = 50) {
  const startOfMonth = new Date()
  startOfMonth.setDate(1)
  startOfMonth.setHours(0, 0, 0, 0)

  const totalCost = await db.apiUsage.aggregate({
    where: { userId, timestamp: { gte: startOfMonth } },
    _sum: { cost: true },
  })

  const spent = totalCost._sum.cost || 0
  if (spent >= monthlyLimit) {
    throw new Error("Monthly AI budget exceeded")
  }
  return { spent, remaining: monthlyLimit - spent }
}
```

---

## Summary

| Feature | Technology | Cost |
|---------|-----------|------|
| Chat (streaming) | GPT-4o-mini | ~$0.15/1M tokens |
| RAG | Embeddings + Pinecone | ~$0.02/1M tokens |
| Function Calling | GPT-4o | ~$2.50/1M tokens |
| Image Generation | DALL-E 3 | ~$0.04/image |
| Agents | GPT-4o + tools | Variable |

**This guide saves ~40-60 hours of AI integration research and implementation.**
