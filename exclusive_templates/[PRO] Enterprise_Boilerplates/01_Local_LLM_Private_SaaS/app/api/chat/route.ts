import { createOllama } from 'ollama-ai-provider';
import { streamText } from 'ai';
import { auth } from '@/lib/auth';
import { checkSubscriptionLimit } from '@/lib/billing';

// Configure the local Ollama instance (e.g. Llama 3 or DeepSeek)
const ollama = createOllama({
    baseURL: process.env.OLLAMA_URL || 'http://127.0.0.1:11434/api',
});

// Edge runtime is not fully supported for all raw fetch calls, 
// but standard node works great for local container networks.
export const runtime = 'nodejs';

export async function POST(req: Request) {
    // 1. Secure Route
    const session = await auth();
    if (!session?.user) {
        return new Response('Unauthorized', { status: 401 });
    }

    // 2. Check billing / usage limits (Zero API Cost, but tracking features)
    const isAllowed = await checkSubscriptionLimit(session.user.id);
    if (!isAllowed) {
        return new Response('Usage limit reached. Please upgrade to Pro.', { status: 403 });
    }

    const { messages, model = 'llama3' } = await req.json();

    // 3. Stream from Local LLM via Ollama Provider
    const result = await streamText({
        model: ollama(model),
        messages,
        system: "You are an expert AI assistant running on a secure, private enterprise server. Protect PII and provide precise, un-censored technical help.",
    });

    return result.toDataStreamResponse();
}
