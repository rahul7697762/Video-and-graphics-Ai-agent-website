
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    try {
        const body = await req.json();

        console.log("Received request body:", JSON.stringify(body, null, 2));

        // Handle both formats:
        // Format 1 (frontend): { mode: "structured", prompt: { category, details }, platform, style }
        // Format 2 (direct): { category, raw_input, ... }

        let pythonPayload;

        if (body.prompt) {
            // Frontend format with prompt wrapper
            pythonPayload = {
                category: body.prompt.category || "ready-to-move",
                raw_input: body.prompt.details || "",
                aspectRatio: body.aspectRatio || "9:16",
                platform: body.platform || "Instagram Story",
                style: body.style || "modern"
            };
        } else {
            // Direct format
            pythonPayload = {
                category: body.category || "ready-to-move",
                raw_input: body.raw_input || body.details || "",
                aspectRatio: body.aspectRatio || "9:16",
                platform: body.platform || "Instagram Story",
                style: body.style || "modern"
            };
        }

        console.log("Python payload:", JSON.stringify(pythonPayload, null, 2));

        // Validate required field
        if (!pythonPayload.raw_input) {
            return NextResponse.json(
                { error: "Property details (raw_input) is required" },
                { status: 400 }
            );
        }

        const pythonUrl = "http://127.0.0.1:8003/api/v2/design/generate";

        console.log("Proxying request to Python backend:", pythonUrl);

        const response = await fetch(pythonUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(pythonPayload),
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Python Backend Error:", response.status, errorText);
            return NextResponse.json(
                { error: `AI Service Error: ${response.status} - ${errorText}` },
                { status: response.status }
            );
        }

        const data = await response.json();

        console.log("Python response received, image size:", data.image?.data?.length || 0);

        return NextResponse.json(data);

    } catch (error: any) {
        console.error("Proxy Error:", error);
        return NextResponse.json(
            { error: error.message || "Failed to connect to AI service" },
            { status: 500 }
        );
    }
}
