"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
    Loader2, Wand2, Download, Image as ImageIcon,
    ThumbsUp, ThumbsDown, Sparkles, Zap, BarChart3
} from "lucide-react";

type ImageData = {
    mimeType: string;
    base64: string;
};

type DesignPlan = {
    visual_prompt: string;
    copy: {
        headline: string;
        subtext: string;
        cta: string;
        keywords: string[];
    };
    layout: {
        title_position: string;
        price_position: string;
        logo_position: string;
        headline_color: string;
        subtext_color: string;
        accent_color: string;
        overlay_type: string;
    };
    reasoning: string;
};

type DesignScores = {
    photorealism: number;
    layout_alignment: number;
    readability: number;
    real_estate_relevance: number;
    overall_quality: number;
};

type GeneratedDesign = {
    id: string;
    imageData: ImageData;
    plan: DesignPlan;
    scores: DesignScores | null;
};

export default function GraphicDesignerPage() {
    const [category, setCategory] = useState("ready-to-move");
    const [platform, setPlatform] = useState("Instagram Story");
    const [style, setStyle] = useState("modern");
    const [details, setDetails] = useState("");
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(0);
    const [generationMode, setGenerationMode] = useState<"single" | "ensemble">("single");

    const [currentDesign, setCurrentDesign] = useState<GeneratedDesign | null>(null);
    const [feedbackSent, setFeedbackSent] = useState(false);

    const handleGenerate = async () => {
        if (!details) return;

        setLoading(true);
        setCurrentDesign(null);
        setFeedbackSent(false);
        setCountdown(30);

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
                    platform,
                    style,
                }),
            });

            const data = await res.json();

            if (data.image?.data) {
                setCurrentDesign({
                    id: data.id || `design_${Date.now()}`,
                    imageData: {
                        mimeType: data.image.mimeType,
                        base64: data.image.data,
                    },
                    plan: data.plan,
                    scores: data.scores || null,
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
        if (!currentDesign) return;

        const link = document.createElement("a");
        link.href = `data:${currentDesign.imageData.mimeType};base64,${currentDesign.imageData.base64}`;
        link.download = `design_${currentDesign.id}.png`;
        link.click();
    };

    const handleFeedback = async (type: "approve" | "reject") => {
        if (!currentDesign) return;

        try {
            await fetch("http://localhost:8003/api/v2/feedback/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    design_id: currentDesign.id,
                    feedback_type: type,
                    rating: type === "approve" ? 5 : 2,
                }),
            });
            setFeedbackSent(true);
        } catch (err) {
            console.error("Feedback failed:", err);
        }
    };

    const getScoreColor = (score: number) => {
        if (score >= 8) return "text-green-500";
        if (score >= 6) return "text-yellow-500";
        return "text-red-500";
    };

    const getAverageScore = (scores: DesignScores) => {
        return ((scores.photorealism + scores.layout_alignment + scores.readability +
            scores.real_estate_relevance + scores.overall_quality) / 5).toFixed(1);
    };

    return (
        <div className="flex flex-col gap-6 p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-2">
                        <Sparkles className="h-8 w-8 text-primary" />
                        AI Graphic Designer
                    </h1>
                    <p className="text-muted-foreground">
                        Generate professional real estate marketing creatives with AI
                    </p>
                </div>
                <Badge variant="secondary" className="text-sm">
                    v2.0 SaaS
                </Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Controls Panel */}
                <div className="border rounded-xl p-6 space-y-6 bg-gradient-to-b from-background to-muted/20">
                    <div className="space-y-4">
                        {/* Category */}
                        <div className="space-y-2">
                            <Label className="font-semibold">Property Category</Label>
                            <Select value={category} onValueChange={setCategory}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select category" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="ready-to-move">🏠 Ready to Move</SelectItem>
                                    <SelectItem value="under-construction">🏗️ New Launch</SelectItem>
                                    <SelectItem value="luxury">💎 Luxury</SelectItem>
                                    <SelectItem value="rental">🔑 Rental</SelectItem>
                                    <SelectItem value="commercial">🏢 Commercial</SelectItem>
                                    <SelectItem value="open-plot">🌳 Open Plot</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Platform */}
                        <div className="space-y-2">
                            <Label className="font-semibold">Target Platform</Label>
                            <Select value={platform} onValueChange={setPlatform}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select platform" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="Instagram Story">📱 Instagram Story</SelectItem>
                                    <SelectItem value="Instagram Post">📷 Instagram Post</SelectItem>
                                    <SelectItem value="Facebook">👥 Facebook</SelectItem>
                                    <SelectItem value="Website Banner">🖥️ Website Banner</SelectItem>
                                    <SelectItem value="Print Flyer A4">📄 Print Flyer (A4)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Style */}
                        <div className="space-y-2">
                            <Label className="font-semibold">Design Style</Label>
                            <Select value={style} onValueChange={setStyle}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select style" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="modern">✨ Modern</SelectItem>
                                    <SelectItem value="luxury">👑 Luxury</SelectItem>
                                    <SelectItem value="minimalist">◻️ Minimalist</SelectItem>
                                    <SelectItem value="premium">💫 Premium</SelectItem>
                                    <SelectItem value="corporate">🏛️ Corporate</SelectItem>
                                    <SelectItem value="rental-friendly">🏡 Rental Friendly</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Details */}
                        <div className="space-y-2">
                            <Label className="font-semibold">Property Details</Label>
                            <Textarea
                                placeholder="3 BHK apartment in Hinjewadi, premium amenities, near IT park, ₹1.5Cr..."
                                value={details}
                                onChange={(e) => setDetails(e.target.value)}
                                className="min-h-[120px] resize-none"
                            />
                            <p className="text-xs text-muted-foreground">
                                Enter raw details. AI will create compelling copy.
                            </p>
                        </div>
                    </div>

                    {/* Generate Button */}
                    <Button
                        onClick={handleGenerate}
                        disabled={loading || !details}
                        size="lg"
                        className="w-full bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
                    >
                        {loading ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Generating ({countdown}s)
                            </>
                        ) : (
                            <>
                                <Wand2 className="mr-2 h-5 w-5" />
                                Generate Creative
                            </>
                        )}
                    </Button>
                </div>

                {/* Preview Panel */}
                <div className="lg:col-span-2 flex flex-col gap-4">
                    <div className="border rounded-xl bg-gradient-to-br from-muted/30 to-muted/50 p-6 flex justify-center min-h-[600px] items-center relative overflow-hidden">
                        {loading && (
                            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/90 backdrop-blur-sm rounded-xl">
                                <div className="relative">
                                    <div className="text-7xl font-bold text-primary animate-pulse">{countdown}</div>
                                    <Sparkles className="absolute -top-2 -right-2 h-6 w-6 text-yellow-500 animate-bounce" />
                                </div>
                                <p className="text-muted-foreground mt-4">Creating your masterpiece...</p>
                                <div className="flex gap-1 mt-4">
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                            </div>
                        )}

                        {currentDesign ? (
                            <div
                                className="relative bg-white shadow-2xl overflow-hidden rounded-lg"
                                style={{
                                    width: "400px",
                                    height: "711px",
                                    transform: "scale(0.85)",
                                    transformOrigin: "center center"
                                }}
                            >
                                <img
                                    src={`data:${currentDesign.imageData.mimeType};base64,${currentDesign.imageData.base64}`}
                                    alt="Generated Design"
                                    className="w-full h-full object-cover"
                                />
                                <div className="absolute top-3 right-3">
                                    <Badge className="bg-primary/90 text-xs">
                                        {category.replace("-", " ")}
                                    </Badge>
                                </div>
                            </div>
                        ) : (
                            !loading && (
                                <div className="text-muted-foreground text-lg flex flex-col items-center gap-3">
                                    <div className="w-24 h-24 rounded-full bg-muted/50 flex items-center justify-center">
                                        <ImageIcon className="w-12 h-12 opacity-30" />
                                    </div>
                                    <span className="font-medium">Ready to generate</span>
                                    <span className="text-sm opacity-70">Enter property details and click Generate</span>
                                </div>
                            )
                        )}
                    </div>

                    {/* Action Buttons */}
                    {currentDesign && (
                        <div className="flex items-center justify-between">
                            <div className="flex gap-2">
                                <Button
                                    variant={feedbackSent ? "secondary" : "outline"}
                                    size="sm"
                                    onClick={() => handleFeedback("approve")}
                                    disabled={feedbackSent}
                                >
                                    <ThumbsUp className="mr-1 h-4 w-4" />
                                    {feedbackSent ? "Thanks!" : "Good"}
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => handleFeedback("reject")}
                                    disabled={feedbackSent}
                                >
                                    <ThumbsDown className="mr-1 h-4 w-4" />
                                    Improve
                                </Button>
                            </div>
                            <Button onClick={handleDownload} size="sm" className="gap-2">
                                <Download className="h-4 w-4" />
                                Download PNG
                            </Button>
                        </div>
                    )}
                </div>

                {/* AI Insights Panel */}
                {currentDesign && (
                    <div className="lg:col-span-3">
                        <Tabs defaultValue="scores" className="w-full">
                            <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-flex">
                                <TabsTrigger value="scores" className="gap-2">
                                    <BarChart3 className="h-4 w-4" />
                                    AI Scores
                                </TabsTrigger>
                                <TabsTrigger value="copy" className="gap-2">
                                    <Zap className="h-4 w-4" />
                                    Copy Strategy
                                </TabsTrigger>
                                <TabsTrigger value="layout" className="gap-2">
                                    <Sparkles className="h-4 w-4" />
                                    Design Logic
                                </TabsTrigger>
                            </TabsList>

                            <TabsContent value="scores" className="border rounded-xl p-6 mt-4">
                                {currentDesign.scores ? (
                                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                        {[
                                            { label: "Photorealism", value: currentDesign.scores.photorealism },
                                            { label: "Layout", value: currentDesign.scores.layout_alignment },
                                            { label: "Readability", value: currentDesign.scores.readability },
                                            { label: "Relevance", value: currentDesign.scores.real_estate_relevance },
                                            { label: "Overall", value: currentDesign.scores.overall_quality },
                                        ].map((score) => (
                                            <div key={score.label} className="text-center p-4 bg-muted/30 rounded-lg">
                                                <div className={`text-3xl font-bold ${getScoreColor(score.value)}`}>
                                                    {score.value.toFixed(1)}
                                                </div>
                                                <div className="text-xs text-muted-foreground mt-1">{score.label}</div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-muted-foreground text-center py-4">
                                        AI scoring not available for this design
                                    </p>
                                )}
                            </TabsContent>

                            <TabsContent value="copy" className="border rounded-xl p-6 mt-4">
                                <div className="grid md:grid-cols-3 gap-4">
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">HEADLINE</Label>
                                        <div className="p-3 bg-muted/30 rounded-lg font-semibold">
                                            {currentDesign.plan.copy.headline}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">SUBTEXT</Label>
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            {currentDesign.plan.copy.subtext}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">CALL TO ACTION</Label>
                                        <div className="p-3 bg-primary/20 rounded-lg font-medium text-primary">
                                            {currentDesign.plan.copy.cta}
                                        </div>
                                    </div>
                                </div>
                            </TabsContent>

                            <TabsContent value="layout" className="border rounded-xl p-6 mt-4">
                                <div className="grid md:grid-cols-2 gap-6">
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">VISUAL PROMPT</Label>
                                        <div className="p-3 bg-muted/30 rounded-lg text-sm font-mono">
                                            {currentDesign.plan.visual_prompt}
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <Label className="text-xs text-muted-foreground">AI REASONING</Label>
                                        <div className="p-3 bg-muted/30 rounded-lg text-sm italic">
                                            "{currentDesign.plan.reasoning}"
                                        </div>
                                    </div>
                                </div>
                            </TabsContent>
                        </Tabs>
                    </div>
                )}
            </div>
        </div>
    );
}
