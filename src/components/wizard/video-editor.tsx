'use client';

import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

export default function VideoEditor() {
    const [step, setStep] = useState(1);
    const [generating, setGenerating] = useState(false);
    const [uploadingState, setUploadingState] = useState<Record<string, boolean>>({});

    // Form data tailored for Creatomate template
    const [formData, setFormData] = useState({
        propertyType: '',
        city: '',
        locality: '',
        carpetArea: '',
        price: '',
        priceLabel: '',
        possessionStatus: '',
        furnishingStatus: '',
        contactPhone: '',
        mediaUrls: {} as Record<string, string>,
        confirmed: false
    });

    const supabase = createClient();
    const router = useRouter();

    const handleInput = (key: string, value: any) => setFormData(prev => ({ ...prev, [key]: value }));

    const uploadMedia = async (key: string, file: File) => {
        if (!file) return;
        setUploadingState(prev => ({ ...prev, [key]: true }));
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error("User auth missing");
            const fileName = `${user.id}/editor/${Date.now()}-${key}.${file.name.split('.').pop()}`;
            const { error } = await supabase.storage.from('video-assets').upload(fileName, file);
            if (error) throw error;
            const { data: { publicUrl } } = supabase.storage.from('video-assets').getPublicUrl(fileName);

            setFormData(prev => ({
                ...prev,
                mediaUrls: { ...prev.mediaUrls, [key]: publicUrl }
            }));
            toast.success(`${key} uploaded`);
        } catch (err: any) {
            toast.error(err.message);
        } finally {
            setUploadingState(prev => ({ ...prev, [key]: false }));
        }
    };

    const handleGenerate = async () => {
        if (!formData.confirmed) {
            toast.error("Please confirm the details.");
            return;
        }
        setGenerating(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error("No user");

            // Create a property record for this Edit (optional but good for data integrity)
            const { data: property, error } = await supabase.from('video_properties').insert({
                user_id: user.id,
                title: `Video Edit - ${formData.propertyType}`,
                description: `Edit Job | ${formData.city}`,
                details: formData
            }).select().single();

            if (error) throw error;

            // Construct payload for Creatomate
            const payload = {
                propertyId: property.id,
                modifications: {
                    "fill_color": "#ffffff",
                    "Video-8P2.source": formData.mediaUrls['mainVideo'],
                    "Image-M79.source": formData.mediaUrls['mainImage'],
                    "Text-QWK.text": `Carpet Area: ${formData.carpetArea || ''} Sq. Ft.\nBasic Cost:   ${formData.priceLabel || formData.price || ''}`,
                    "Text-MFP.text": `${formData.propertyType || ''} | ${formData.possessionStatus || ''}\n${formData.furnishingStatus || ''} | Limited Units`,
                    "Text-R85.text": formData.contactPhone || 'Contact Agent',
                    "Text-V22.text": `📍 ${formData.locality || ''} - ${formData.city || ''}`,
                    "Text-V22.fill_color": "rgba(255,255,255,1)"
                }
            };

            const res = await fetch('/api/creatomate/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await res.json();
            if (!res.ok) throw new Error(result.error);

            toast.success("Rendering started!");
            router.push(`/videos/${result.videoId}`);

        } catch (e: any) {
            toast.error(e.message);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto p-8 bg-card rounded-xl shadow-lg border my-10">
            <div className="mb-8 border-b pb-4">
                <h2 className="text-3xl font-bold tracking-tight">Video Editor</h2>
                <p className="text-sm text-muted-foreground mt-2">
                    Create professional real estate reels in minutes.
                </p>
                <div className="flex gap-2 mt-4">
                    {[1, 2, 3].map(s => (
                        <div key={s} className={`h-2 flex-1 rounded-full ${step >= s ? 'bg-indigo-600' : 'bg-secondary'}`} />
                    ))}
                </div>
            </div>

            {/* Step 1: Text Details */}
            {step === 1 && (
                <div className="space-y-6 animate-in slide-in-from-right-4 fade-in">
                    <h3 className="text-lg font-semibold">1. Property Details</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <Label>Property Type</Label>
                            <Input placeholder="3 BHK Apartment" value={formData.propertyType} onChange={e => handleInput('propertyType', e.target.value)} />
                        </div>
                        <div>
                            <Label>City</Label>
                            <Input placeholder="Pune" value={formData.city} onChange={e => handleInput('city', e.target.value)} />
                        </div>
                        <div>
                            <Label>Locality</Label>
                            <Input placeholder="Hinjewadi" value={formData.locality} onChange={e => handleInput('locality', e.target.value)} />
                        </div>
                        <div>
                            <Label>Carpet Area (Sq. Ft.)</Label>
                            <Input placeholder="1200" value={formData.carpetArea} onChange={e => handleInput('carpetArea', e.target.value)} />
                        </div>
                        <div>
                            <Label>Price Label</Label>
                            <Input placeholder="₹1.25 Cr" value={formData.priceLabel} onChange={e => handleInput('priceLabel', e.target.value)} />
                        </div>
                        <div>
                            <Label>Possession Status</Label>
                            <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.possessionStatus} onChange={e => handleInput('possessionStatus', e.target.value)}>
                                <option value="">Select</option>
                                <option value="Ready to Move">Ready to Move</option>
                                <option value="Under Construction">Under Construction</option>
                            </select>
                        </div>
                        <div>
                            <Label>Furnishing</Label>
                            <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.furnishingStatus} onChange={e => handleInput('furnishingStatus', e.target.value)}>
                                <option value="">Select</option>
                                <option value="Unfurnished">Unfurnished</option>
                                <option value="Semi-Furnished">Semi-Furnished</option>
                                <option value="Fully Furnished">Fully Furnished</option>
                            </select>
                        </div>
                        <div>
                            <Label>Contact Phone</Label>
                            <Input placeholder="+91 99999 99999" value={formData.contactPhone} onChange={e => handleInput('contactPhone', e.target.value)} />
                        </div>
                    </div>
                    <div className="flex justify-end pt-4">
                        <Button onClick={() => setStep(2)}>Next: Assets</Button>
                    </div>
                </div>
            )}

            {/* Step 2: Uploads */}
            {step === 2 && (
                <div className="space-y-6 animate-in slide-in-from-right-4 fade-in">
                    <h3 className="text-lg font-semibold">2. Upload Assets</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="border p-4 rounded-lg bg-muted/20">
                            <Label className="mb-2 block">Main Video (Background)</Label>
                            {formData.mediaUrls.mainVideo ? (
                                <div className="relative h-48 w-full">
                                    <video src={formData.mediaUrls.mainVideo} className="h-full w-full object-cover rounded" controls />
                                    <Button variant="destructive" size="icon" className="absolute top-1 right-1 h-6 w-6" onClick={() => {
                                        const newUrls = { ...formData.mediaUrls };
                                        delete newUrls.mainVideo;
                                        setFormData(prev => ({ ...prev, mediaUrls: newUrls }));
                                    }}>x</Button>
                                </div>
                            ) : (
                                <div
                                    className="flex flex-col items-center justify-center p-8 border-2 border-dashed rounded cursor-pointer hover:bg-muted transition-colors"
                                    onClick={() => document.getElementById('video-upload')?.click()}
                                >
                                    <span className="text-2xl mb-2">📹</span>
                                    <span className="text-sm font-medium">{uploadingState.mainVideo ? 'Uploading...' : 'Upload Video File'}</span>
                                    <input id="video-upload" type="file" className="hidden" accept="video/*" onChange={e => e.target.files && uploadMedia('mainVideo', e.target.files[0])} />
                                </div>
                            )}
                        </div>

                        <div className="border p-4 rounded-lg bg-muted/20">
                            <Label className="mb-2 block">Overlay Image (Inset)</Label>
                            {formData.mediaUrls.mainImage ? (
                                <div className="relative h-48 w-full">
                                    <img src={formData.mediaUrls.mainImage} className="h-full w-full object-cover rounded" />
                                    <Button variant="destructive" size="icon" className="absolute top-1 right-1 h-6 w-6" onClick={() => {
                                        const newUrls = { ...formData.mediaUrls };
                                        delete newUrls.mainImage;
                                        setFormData(prev => ({ ...prev, mediaUrls: newUrls }));
                                    }}>x</Button>
                                </div>
                            ) : (
                                <div
                                    className="flex flex-col items-center justify-center p-8 border-2 border-dashed rounded cursor-pointer hover:bg-muted transition-colors"
                                    onClick={() => document.getElementById('image-upload')?.click()}
                                >
                                    <span className="text-2xl mb-2">🖼️</span>
                                    <span className="text-sm font-medium">{uploadingState.mainImage ? 'Uploading...' : 'Upload Image File'}</span>
                                    <input id="image-upload" type="file" className="hidden" accept="image/*" onChange={e => e.target.files && uploadMedia('mainImage', e.target.files[0])} />
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="flex justify-between pt-4">
                        <Button variant="outline" onClick={() => setStep(1)}>Back</Button>
                        <Button onClick={() => setStep(3)} disabled={!formData.mediaUrls.mainVideo || !formData.mediaUrls.mainImage}>Next: Review</Button>
                    </div>
                </div>
            )}

            {/* Step 3: Review */}
            {step === 3 && (
                <div className="space-y-6 animate-in slide-in-from-right-4 fade-in">
                    <h3 className="text-lg font-semibold">3. Review & Render</h3>
                    <div className="bg-slate-50 p-6 rounded-lg text-sm space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                            <div><span className="font-semibold">Type:</span> {formData.propertyType}</div>
                            <div><span className="font-semibold">Location:</span> {formData.locality}, {formData.city}</div>
                            <div><span className="font-semibold">Price:</span> {formData.priceLabel}</div>
                            <div><span className="font-semibold">Area:</span> {formData.carpetArea} sq.ft</div>
                            <div><span className="font-semibold">Phone:</span> {formData.contactPhone}</div>
                        </div>
                        <div className="pt-2 border-t mt-2">
                            <div className="flex gap-2 items-center text-green-700">
                                <span className="text-lg">✓</span> All assets uploaded
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            id="confirm"
                            checked={formData.confirmed}
                            onChange={e => handleInput('confirmed', e.target.checked)}
                            className="h-4 w-4 rounded border-gray-300 text-indigo-600"
                        />
                        <Label htmlFor="confirm">I confirm the details are correct.</Label>
                    </div>

                    <div className="flex justify-between pt-4">
                        <Button variant="outline" onClick={() => setStep(2)}>Back</Button>
                        <Button
                            className="bg-indigo-600 hover:bg-indigo-700 w-40"
                            onClick={handleGenerate}
                            disabled={!formData.confirmed || generating}
                        >
                            {generating ? 'Processing...' : 'Run Render'}
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
