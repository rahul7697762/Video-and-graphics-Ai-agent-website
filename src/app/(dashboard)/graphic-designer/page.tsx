"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Loader2, Wand2, Download, Image as ImageIcon } from "lucide-react";

type ImageData = {
    mimeType: string;
    base64: string;
};

export default function GraphicDesignerPage() {
    const [category, setCategory] = useState("ready-to-move");
    const [details, setDetails] = useState("");
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(0);

    const [imageData, setImageData] = useState<ImageData | null>(null);
    const [copy, setCopy] = useState("");

    const handleGenerate = async () => {
        if (!details) return;

        setLoading(true);
        setImageData(null);
        setCopy("");
        setCountdown(30); // Start 30s countdown

        const timer = setInterval(() => {
            setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
        }, 1000);

        try {
            const res = await fetch("/api/gemini/design", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    mode: "structured",
                    prompt: {
                        category,
                        details,
                    },
                }),
            });

            const data = await res.json();

            if (data.image?.data) {
                setImageData({
                    mimeType: data.image.mimeType,
                    base64: data.image.data,
                });
            }
        } catch (err) {
            console.error(err);
            alert("Failed to generate design");
        } finally {
            setLoading(false);
            clearInterval(timer);
            setCountdown(0);
        }
    };

    const handleDownload = () => {
        if (!imageData) return;

        const link = document.createElement("a");
        link.href = `data:${imageData.mimeType};base64,${imageData.base64}`;
        link.download = `design_${Date.now()}.png`;
        link.click();
    };

    return (
        <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold">AI Graphic Designer</h1>
                <p className="text-muted-foreground">
                    Generate professional real estate creatives using AI
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Controls */}
                <div className="border rounded-xl p-6 space-y-6">
                    <div className="space-y-2">
                        <Label>Property Category</Label>
                        <Select value={category} onValueChange={setCategory}>
                            <SelectTrigger>
                                <SelectValue placeholder="Select category" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="ready-to-move">Ready to Move</SelectItem>
                                <SelectItem value="under-construction">New Launch</SelectItem>
                                <SelectItem value="luxury">Luxury</SelectItem>
                                <SelectItem value="rental">Rental</SelectItem>
                                <SelectItem value="commercial">Commercial</SelectItem>
                                <SelectItem value="open-plot">Open Plot</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Property Details</Label>
                        <Textarea
                            placeholder="3 BHK apartment in Hinjewadi, premium amenities, near IT park..."
                            value={details}
                            onChange={(e) => setDetails(e.target.value)}
                            className="min-h-[120px]"
                        />
                        <p className="text-xs text-muted-foreground">
                            Enter raw details. AI will refine them.
                        </p>
                    </div>

                    <Button
                        onClick={handleGenerate}
                        disabled={loading || !details}
                        size="lg"
                        className="w-full"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Generating ({countdown}s)
                            </>
                        ) : (
                            <>
                                <Wand2 className="mr-2 h-4 w-4" />
                                Generate Creative
                            </>
                        )}
                    </Button>
                </div>

                {/* Preview */}
                <div className="lg:col-span-2 flex flex-col gap-4">
                    <div className="border rounded-xl bg-muted/50 p-6 flex justify-center min-h-[600px] items-center relative">
                        {loading && (
                            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/80 backdrop-blur-sm rounded-xl">
                                <div className="text-6xl font-bold text-primary animate-pulse">{countdown}</div>
                                <p className="text-muted-foreground mt-4">Creating your masterpiece...</p>
                            </div>
                        )}

                        {imageData ? (
                            <div
                                className="relative bg-white shadow-xl overflow-hidden"
                                style={{
                                    width: "540px",
                                    height: "960px", // 9:16 preview (HD vertical)
                                    transform: "scale(0.8)", // Slight scale down to fit if needed, or remove for full size scrolling
                                    transformOrigin: "center top"
                                }}
                            >
                                {/* Image */}
                                <img
                                    src={`data:${imageData.mimeType};base64,${imageData.base64}`}
                                    alt="Generated"
                                    className="w-full h-full object-cover"
                                />

                                {/* Category Badge */}
                                <div className="absolute top-4 right-4 bg-primary text-primary-foreground text-xs px-3 py-1 rounded shadow-md z-20">
                                    {category.replace("-", " ")}
                                </div>
                            </div>
                        ) : (
                            !loading && (
                                <div className="text-muted-foreground text-lg flex flex-col items-center gap-2">
                                    <ImageIcon className="w-12 h-12 opacity-20" />
                                    <span>Ready to generate</span>
                                </div>
                            )
                        )}
                    </div>

                    {imageData && (
                        <div className="flex justify-end">
                            <Button variant="secondary" onClick={handleDownload} size="lg">
                                <Download className="mr-2 h-4 w-4" />
                                Download PNG
                            </Button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
