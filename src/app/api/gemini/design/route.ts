
import { NextResponse } from "next/server";

export async function POST(req: Request) {
    try {
        const body = await req.json();

        // Transform Request: Next.js Frontend -> Python Microservice
        // Frontend sends: { mode: "structured", prompt: { category, details } }
        // Python expects: { category, raw_input, aspectRatio }

        const pythonPayload = {
            category: body.prompt.category,
            raw_input: body.prompt.details,
            aspectRatio: "9:16" // Updated to 9:16 as requested
        };

        // Forward to Python Backend
        // Assuming running on localhost:8000
        const pythonUrl = "http://127.0.0.1:8000/generate-design";

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
            throw new Error(`AI Service Error: ${response.statusText}`);
        }

        const data = await response.json();

        // Pass the Python response directly back to Frontend
        // Python returns: { image: { ... }, copy: { ... }, meta: { ... } }
        // Frontend expects roughly this structure now.
        return NextResponse.json(data);

    } catch (error: any) {
        console.error("Proxy Error:", error);
        return NextResponse.json(
            { error: error.message || "Failed to connect to AI service" },
            { status: 500 }
        );
    }
}
