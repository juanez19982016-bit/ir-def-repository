// ============================================================
// 🤖 AI/LLM INTEGRATION TOOLKIT — March 2026 Edition
// DevVault Pro — Production-ready AI patterns for Next.js
// ============================================================

// ── 1. Streaming Chat with OpenAI ───────────────

import OpenAI from 'openai'
import { NextRequest } from 'next/server'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })

// app/api/chat/route.ts — Streaming chat endpoint
export async function POST(req: NextRequest) {
    const { messages, model = 'gpt-4o' } = await req.json()

    const stream = await openai.chat.completions.create({
        model,
        messages,
        stream: true,
        temperature: 0.7,
        max_tokens: 4096,
    })

    // Stream response using ReadableStream
    const encoder = new TextEncoder()
    const readable = new ReadableStream({
        async start(controller) {
            for await (const chunk of stream) {
                const text = chunk.choices[0]?.delta?.content || ''
                if (text) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`))
                }
            }
            controller.enqueue(encoder.encode('data: [DONE]\n\n'))
            controller.close()
        },
    })

    return new Response(readable, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
        },
    })
}


// ── 2. RAG (Retrieval-Augmented Generation) ─────

// lib/rag.ts — Complete RAG pipeline

interface Document {
    id: string
    content: string
    metadata: Record<string, any>
    embedding?: number[]
}

// Generate embeddings for documents
export async function generateEmbedding(text: string): Promise<number[]> {
    const response = await openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: text,
    })
    return response.data[0].embedding
}

// Calculate cosine similarity between two vectors
function cosineSimilarity(a: number[], b: number[]): number {
    let dot = 0, normA = 0, normB = 0
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i]
        normA += a[i] ** 2
        normB += b[i] ** 2
    }
    return dot / (Math.sqrt(normA) * Math.sqrt(normB))
}

// Simple in-memory vector store (use Pinecone/Weaviate in production)
class VectorStore {
    private documents: (Document & { embedding: number[] })[] = []

    async addDocument(doc: Document) {
        const embedding = await generateEmbedding(doc.content)
        this.documents.push({ ...doc, embedding })
    }

    async addDocuments(docs: Document[]) {
        await Promise.all(docs.map(doc => this.addDocument(doc)))
    }

    async search(query: string, topK = 5): Promise<Document[]> {
        const queryEmbedding = await generateEmbedding(query)

        return this.documents
            .map(doc => ({
                ...doc,
                score: cosineSimilarity(queryEmbedding, doc.embedding),
            }))
            .sort((a, b) => b.score - a.score)
            .slice(0, topK)
    }
}

// RAG query function
export async function ragQuery(question: string, vectorStore: VectorStore) {
    // 1. Retrieve relevant documents
    const relevantDocs = await vectorStore.search(question, 5)

    // 2. Build context from retrieved documents
    const context = relevantDocs
        .map(doc => doc.content)
        .join('\n\n---\n\n')

    // 3. Generate answer with context
    const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages: [
            {
                role: 'system',
                content: `You are a helpful assistant. Answer questions based on the provided context. 
If the answer isn't in the context, say so. Always cite your sources.

Context:
${context}`,
            },
            { role: 'user', content: question },
        ],
        temperature: 0.3,
    })

    return {
        answer: response.choices[0].message.content,
        sources: relevantDocs.map(d => d.metadata),
    }
}


// ── 3. Function Calling / Tool Use ──────────────

// Define tools for the AI to use
const tools: OpenAI.ChatCompletionTool[] = [
    {
        type: 'function',
        function: {
            name: 'search_products',
            description: 'Search for products in the database',
            parameters: {
                type: 'object',
                properties: {
                    query: { type: 'string', description: 'Search query' },
                    category: { type: 'string', enum: ['electronics', 'clothing', 'books'] },
                    maxPrice: { type: 'number', description: 'Maximum price filter' },
                },
                required: ['query'],
            },
        },
    },
    {
        type: 'function',
        function: {
            name: 'get_order_status',
            description: 'Get the status of an order by ID',
            parameters: {
                type: 'object',
                properties: {
                    orderId: { type: 'string', description: 'The order ID' },
                },
                required: ['orderId'],
            },
        },
    },
    {
        type: 'function',
        function: {
            name: 'create_support_ticket',
            description: 'Create a customer support ticket',
            parameters: {
                type: 'object',
                properties: {
                    subject: { type: 'string' },
                    description: { type: 'string' },
                    priority: { type: 'string', enum: ['low', 'medium', 'high', 'urgent'] },
                },
                required: ['subject', 'description'],
            },
        },
    },
]

// Process function calls
async function processWithTools(userMessage: string) {
    const messages: OpenAI.ChatCompletionMessageParam[] = [
        { role: 'system', content: 'You are a helpful e-commerce assistant. Use the available tools to help customers.' },
        { role: 'user', content: userMessage },
    ]

    const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        messages,
        tools,
        tool_choice: 'auto',
    })

    const message = response.choices[0].message

    // If the model wants to call a function
    if (message.tool_calls) {
        const toolResults = await Promise.all(
            message.tool_calls.map(async (call) => {
                const args = JSON.parse(call.function.arguments)
                let result: any

                switch (call.function.name) {
                    case 'search_products':
                        result = await searchProducts(args.query, args.category, args.maxPrice)
                        break
                    case 'get_order_status':
                        result = await getOrderStatus(args.orderId)
                        break
                    case 'create_support_ticket':
                        result = await createTicket(args.subject, args.description, args.priority)
                        break
                }

                return {
                    role: 'tool' as const,
                    tool_call_id: call.id,
                    content: JSON.stringify(result),
                }
            })
        )

        // Get final response with tool results
        messages.push(message, ...toolResults)
        const finalResponse = await openai.chat.completions.create({
            model: 'gpt-4o',
            messages,
        })

        return finalResponse.choices[0].message.content
    }

    return message.content
}


// ── 4. AI Agent with Memory ─────────────────────

interface AgentMemory {
    shortTerm: Array<{ role: string; content: string }>
    longTerm: VectorStore
    summary: string
}

class AIAgent {
    private memory: AgentMemory
    private systemPrompt: string

    constructor(systemPrompt: string) {
        this.systemPrompt = systemPrompt
        this.memory = {
            shortTerm: [],
            longTerm: new VectorStore(),
            summary: '',
        }
    }

    async chat(userMessage: string): Promise<string> {
        // Add to short-term memory
        this.memory.shortTerm.push({ role: 'user', content: userMessage })

        // Keep only last 20 messages in short-term
        if (this.memory.shortTerm.length > 20) {
            const removed = this.memory.shortTerm.splice(0, 10)
            // Summarize and store in long-term
            const summary = await this.summarize(removed)
            this.memory.summary = summary
        }

        // Search long-term memory for relevant context
        const relevantMemories = await this.memory.longTerm.search(userMessage, 3)

        const response = await openai.chat.completions.create({
            model: 'gpt-4o',
            messages: [
                {
                    role: 'system',
                    content: `${this.systemPrompt}

Previous conversation summary: ${this.memory.summary}
Relevant memories: ${relevantMemories.map(m => m.content).join('\n')}`,
                },
                ...this.memory.shortTerm.map(m => ({
                    role: m.role as 'user' | 'assistant',
                    content: m.content,
                })),
            ],
        })

        const reply = response.choices[0].message.content!
        this.memory.shortTerm.push({ role: 'assistant', content: reply })

        return reply
    }

    private async summarize(messages: Array<{ role: string; content: string }>): Promise<string> {
        const response = await openai.chat.completions.create({
            model: 'gpt-4o-mini',
            messages: [
                { role: 'system', content: 'Summarize this conversation in 2-3 sentences.' },
                { role: 'user', content: messages.map(m => `${m.role}: ${m.content}`).join('\n') },
            ],
        })
        return response.choices[0].message.content!
    }
}


// ── 5. Structured Output (JSON Mode) ────────────

import { z } from 'zod'

const ProductAnalysisSchema = z.object({
    sentiment: z.enum(['positive', 'negative', 'neutral']),
    score: z.number().min(0).max(1),
    keyTopics: z.array(z.string()),
    summary: z.string(),
    actionItems: z.array(z.object({
        priority: z.enum(['high', 'medium', 'low']),
        description: z.string(),
    })),
})

type ProductAnalysis = z.infer<typeof ProductAnalysisSchema>

async function analyzeReview(review: string): Promise<ProductAnalysis> {
    const response = await openai.chat.completions.create({
        model: 'gpt-4o',
        response_format: { type: 'json_object' },
        messages: [
            {
                role: 'system',
                content: `Analyze product reviews. Return JSON with: sentiment, score (0-1), keyTopics, summary, actionItems.`,
            },
            { role: 'user', content: review },
        ],
    })

    const result = JSON.parse(response.choices[0].message.content!)
    return ProductAnalysisSchema.parse(result)
}


// ── 6. Image Generation (DALL-E 3) ──────────────

async function generateImage(prompt: string, size: '1024x1024' | '1792x1024' = '1024x1024') {
    const response = await openai.images.generate({
        model: 'dall-e-3',
        prompt,
        n: 1,
        size,
        quality: 'hd',
    })

    return {
        url: response.data[0].url,
        revisedPrompt: response.data[0].revised_prompt,
    }
}


// ── 7. Text-to-Speech ──────────────────────────

async function textToSpeech(text: string, voice: 'alloy' | 'echo' | 'fable' | 'onyx' | 'nova' = 'nova') {
    const response = await openai.audio.speech.create({
        model: 'tts-1-hd',
        voice,
        input: text,
    })

    const buffer = Buffer.from(await response.arrayBuffer())
    return buffer // Save to file or stream to client
}


// ── 8. Moderation / Content Safety ──────────────

async function moderateContent(input: string) {
    const response = await openai.moderations.create({ input })
    const result = response.results[0]

    return {
        flagged: result.flagged,
        categories: Object.entries(result.categories)
            .filter(([_, flagged]) => flagged)
            .map(([category]) => category),
        scores: result.category_scores,
    }
}
