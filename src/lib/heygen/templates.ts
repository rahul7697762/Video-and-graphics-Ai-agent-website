/* =========================================
   TYPES
========================================= */

export type ScenePurpose =
    | "Hook"
    | "First Impression"
    | "Comfort"
    | "Functionality"
    | "Lifestyle"
    | "View"
    | "Urgency"
    | "Conversion";

export type MediaAssets = {
    exterior: string; // Photo_Building
    entry: string;    // Photo_TV_Hall
    bedroom: string;  // Photo_Bedroom
    kitchen: string;  // Photo_Kitchen
    dining: string;   // Photo_TV_Hall / Dining
    balcony: string;  // Photo_Balcony
    cta: string;      // Reuse exterior / branding frame
};

export type SceneConfig = {
    scene: number;
    duration: number; // seconds (approx, TTS-controlled)
    hasAvatar: boolean;
    text: string;
    mediaKey: keyof MediaAssets;
    purpose: ScenePurpose;
};

/* =========================================
   SCENE CONFIG
========================================= */

export const REAL_ESTATE_WALKTHROUGH: SceneConfig[] = [
    {
        scene: 1,
        duration: 5,
        hasAvatar: true,
        text: "Welcome to a ready-to-move premium home. Limited units available.",
        mediaKey: "exterior",
        purpose: "Urgency"
    },
    {
        scene: 2,
        duration: 5,
        hasAvatar: false,
        text: "As you enter, you’re welcomed by a spacious and well-planned living area.",
        mediaKey: "entry",
        purpose: "First Impression"
    },
    {
        scene: 3,
        duration: 5,
        hasAvatar: false,
        text: "The bedroom is designed for comfort, privacy, and peaceful living.",
        mediaKey: "bedroom",
        purpose: "Comfort"
    },
    {
        scene: 4,
        duration: 5,
        hasAvatar: false,
        text: "This modern kitchen is thoughtfully designed for everyday convenience.",
        mediaKey: "kitchen",
        purpose: "Functionality"
    },
    {
        scene: 5,
        duration: 5,
        hasAvatar: false,
        text: "An ideal dining space for everyday meals and family moments.",
        mediaKey: "dining",
        purpose: "Lifestyle"
    },
    {
        scene: 6,
        duration: 5,
        hasAvatar: false,
        text: "Step into the balcony and enjoy fresh air with an open view.",
        mediaKey: "balcony",
        purpose: "View"
    },
    {
        scene: 7,
        duration: 5,
        hasAvatar: true,
        text: "Book your site visit today. Call or WhatsApp on the displayed number.",
        mediaKey: "cta",
        purpose: "Conversion"
    }
];

/* =========================================
   HELPERS
========================================= */

// Avatar-only script (for TTS / HeyGen avatar)
export function getAvatarScript(): string {
    return REAL_ESTATE_WALKTHROUGH
        .filter(scene => scene.hasAvatar)
        .map(scene => scene.text)
        .join(" ");
}

// Full script (for subtitles / captions)
export function getFullScript(): string {
    return REAL_ESTATE_WALKTHROUGH
        .map(scene => scene.text)
        .join(" ");
}

// Resolve media URL from uploaded assets
export function resolveMedia(
    scene: SceneConfig,
    assets: MediaAssets
): string {
    return assets[scene.mediaKey];
}

// Build render-ready payload (example)
export function buildRenderPayload(assets: MediaAssets) {
    return REAL_ESTATE_WALKTHROUGH.map(scene => ({
        scene: scene.scene,
        duration: scene.duration,
        avatar: scene.hasAvatar,
        text: scene.text,
        mediaUrl: resolveMedia(scene, assets),
        purpose: scene.purpose
    }));
}
