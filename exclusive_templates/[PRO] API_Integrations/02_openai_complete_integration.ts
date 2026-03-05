// ============================================================
// 🤖 OPENAI / AI INTEGRATION — COMPLETE TOOLKIT
// ============================================================
// Everything you need to add AI features to any Next.js app.
// Includes: Chat, Streaming, RAG, Embeddings, Image Gen
// Time saved: ~25-35 hours
// ============================================================

// ============ FILE: lib/openai.ts ============
import OpenAI from "openai";

export const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

// Model configurations for different use cases
export const MODELS = {
    fast: "gpt-4o-mini",        // Cheap, fast — chat, simple tasks
    smart: "gpt-4o",            // Best quality — complex reasoning
    embedding: "text-embedding-3-small", // Vector embeddings
    image: "dall-e-3",          // Image generation
} as const;

// ============ FILE: app/api/ai/chat/route.ts ============
// Streaming AI chat endpoint
import { openai, MODELS } from "@/lib/openai";
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export const runtime = "edge"; // Edge runtime for faster responses

export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { messages, model = "fast" } = await req.json();

    // Add system prompt
    const systemMessage = {
        role: "system" as const,
        content: `You are a helpful assistant. Current date: ${new Date().toISOString().split("T")[0]}. User: ${session.user.name}`,
    };

    const response = await openai.chat.completions.create({
        model: MODELS[model as keyof typeof MODELS] || MODELS.fast,
        messages: [systemMessage, ...messages],
        stream: true,
        temperature: 0.7,
        max_tokens: 2000,
    });

    // Stream the response
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
        async start(controller) {
            for await (const chunk of response) {
                const text = chunk.choices[0]?.delta?.content || "";
                if (text) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ text })}\n\n`));
                }
            }
            controller.enqueue(encoder.encode("data: [DONE]\n\n"));
            controller.close();
        },
    });

    return new Response(stream, {
        headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            Connection: "keep-alive",
        },
    });
}

// ============ FILE: hooks/use-ai-chat.ts ============
// React hook for AI chat with streaming
"use client";
import { useState, useCallback, useRef } from "react";

interface Message {
    role: "user" | "assistant";
    content: string;
}

export function useAIChat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [streamingText, setStreamingText] = useState("");
    const abortRef = useRef<AbortController | null>(null);

    const send = useCallback(async (userMessage: string) => {
        const newMessages: Message[] = [...messages, { role: "user", content: userMessage }];
        setMessages(newMessages);
        setIsLoading(true);
        setStreamingText("");

        abortRef.current = new AbortController();

        try {
            const res = await fetch("/api/ai/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ messages: newMessages }),
                signal: abortRef.current.signal,
            });

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();
            let fullText = "";

            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

                for (const line of lines) {
                    const data = line.slice(6);
                    if (data === "[DONE]") break;
                    try {
                        const { text } = JSON.parse(data);
                        fullText += text;
                        setStreamingText(fullText);
                    } catch { }
                }
            }

            setMessages([...newMessages, { role: "assistant", content: fullText }]);
            setStreamingText("");
        } catch (err) {
            if ((err as Error).name !== "AbortError") {
                console.error("Chat error:", err);
            }
        } finally {
            setIsLoading(false);
        }
    }, [messages]);

    const stop = useCallback(() => {
        abortRef.current?.abort();
        setIsLoading(false);
    }, []);

    const reset = useCallback(() => {
        setMessages([]);
        setStreamingText("");
        setIsLoading(false);
    }, []);

    return { messages, streamingText, isLoading, send, stop, reset };
}

// ============ FILE: app/api/ai/generate-image/route.ts ============
// AI image generation endpoint
import { openai, MODELS } from "@/lib/openai";
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { prompt, size = "1024x1024", quality = "standard" } = await req.json();

    const response = await openai.images.generate({
        model: MODELS.image,
        prompt,
        n: 1,
        size: size as "1024x1024" | "1792x1024" | "1024x1792",
        quality: quality as "standard" | "hd",
    });

    return NextResponse.json({
        url: response.data[0]?.url,
        revisedPrompt: response.data[0]?.revised_prompt,
    });
}

// ============ FILE: app/api/ai/summarize/route.ts ============
// Text summarization endpoint
import { openai, MODELS } from "@/lib/openai";
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { text, style = "concise" } = await req.json();

    const styles = {
        concise: "Summarize in 2-3 sentences.",
        bullets: "Summarize as bullet points (max 5).",
        executive: "Write an executive summary with key takeaways.",
        tweet: "Summarize in under 280 characters for Twitter.",
    };

    const response = await openai.chat.completions.create({
        model: MODELS.fast,
        messages: [
            { role: "system", content: `You are an expert summarizer. ${styles[style as keyof typeof styles]}` },
            { role: "user", content: text },
        ],
        temperature: 0.3,
    });

    return NextResponse.json({
        summary: response.choices[0]?.message?.content,
        usage: response.usage,
    });
}

// ============ FILE: app/api/ai/embeddings/route.ts ============
// Vector embeddings for semantic search / RAG
import { openai, MODELS } from "@/lib/openai";
import { auth } from "@/auth";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    const session = await auth();
    if (!session?.user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { texts } = await req.json(); // Array of strings

    const response = await openai.embeddings.create({
        model: MODELS.embedding,
        input: texts,
    });

    return NextResponse.json({
        embeddings: response.data.map((d) => d.embedding),
        usage: response.usage,
    });
}

// ============ FILE: lib/ai-utils.ts ============
// Utility functions for AI features

// Calculate cosine similarity between two vectors
export function cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < a.length; i++) {
        dotProduct += a[i] * b[i];
        normA += a[i] * a[i];
        normB += b[i] * b[i];
    }
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

// Simple RAG: find most relevant documents
export async function findRelevantDocs(
    query: string,
    documents: { text: string; embedding: number[] }[],
    topK = 3
): Promise<{ text: string; score: number }[]> {
    const res = await fetch("/api/ai/embeddings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texts: [query] }),
    });
    const { embeddings } = await res.json();
    const queryEmbedding = embeddings[0];

    return documents
        .map((doc) => ({
            text: doc.text,
            score: cosineSimilarity(queryEmbedding, doc.embedding),
        }))
        .sort((a, b) => b.score - a.score)
        .slice(0, topK);
}

// Token estimation (rough)
export function estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
}

// Cost estimation
export function estimateCost(inputTokens: number, outputTokens: number, model = "gpt-4o-mini") {
    const pricing = {
        "gpt-4o-mini": { input: 0.15 / 1_000_000, output: 0.6 / 1_000_000 },
        "gpt-4o": { input: 2.5 / 1_000_000, output: 10 / 1_000_000 },
    };
    const p = pricing[model as keyof typeof pricing] || pricing["gpt-4o-mini"];
    return {
        inputCost: inputTokens * p.input,
        outputCost: outputTokens * p.output,
        totalCost: inputTokens * p.input + outputTokens * p.output,
    };
}
