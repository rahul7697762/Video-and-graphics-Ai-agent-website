import { NextResponse } from 'next/server';

const MCP_BACKEND_URL = process.env.MCP_BACKEND_URL || 'http://localhost:8001';

export async function POST(req: Request) {
    try {
        const body = await req.json();
        const { prompt } = body;

        if (!prompt) {
            return NextResponse.json({ error: 'Prompt is required' }, { status: 400 });
        }

        // Forward request to Python MCP Backend
        const response = await fetch(`${MCP_BACKEND_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json({ error: data.detail || 'MCP service error' }, { status: response.status });
        }

        return NextResponse.json(data);

    } catch (error: any) {
        console.error('MCP Proxy Error:', error);

        // Check if it's a connection error
        if (error.code === 'ECONNREFUSED') {
            return NextResponse.json({
                error: 'MCP service is not running. Please start the Python backend.'
            }, { status: 503 });
        }

        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
