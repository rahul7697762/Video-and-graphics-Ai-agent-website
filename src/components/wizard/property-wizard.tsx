'use client';

import { useState, useEffect } from 'react';
import { createClient } from '@/lib/supabase/client';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { Label } from '@/components/ui/label';

export default function PropertyWizard({ forcedCategory, allowedCategories }: { forcedCategory?: string, allowedCategories?: string[] }) {
    const [step, setStep] = useState(forcedCategory ? 1 : 0); // Start at Step 1 if forced
    const [formData, setFormData] = useState<any>({
        category: forcedCategory || '', // Use forced category if present
        propertyId: '',
        projectName: '',
        propertyType: '',
        city: '',
        locality: '',
        builder: '',
        carpetArea: '',
        floor: '',
        totalFloors: '',
        furnishingStatus: '',
        facing: '',
        price: '',
        priceLabel: '',
        possessionStatus: '',
        parking: '',
        availability: 'Available',
        amenities: 'Swimming Pool:Yes | Gym:Yes | Clubhouse:Yes | Play Area:Yes | CCTV:Yes | Security:Yes | Power Backup:Yes | Lift:Yes | Parking:Yes | Garden:No',
        mediaUrls: {},
        videoLanguage: 'English',
        avatarId: '',
        voiceId: '',
        confirmed: false,
        // contactPhone: '' // Removed
    });

    const [generating, setGenerating] = useState(false);
    const [uploadingState, setUploadingState] = useState<Record<string, boolean>>({});
    const [avatars, setAvatars] = useState<any[]>([]);
    const [voices, setVoices] = useState<any[]>([]);
    const [loadingConfig, setLoadingConfig] = useState(false);

    useEffect(() => {
        const fetchConfig = async () => {
            setLoadingConfig(true);
            try {
                const [avatarsRes, voicesRes] = await Promise.all([
                    fetch('/api/heygen/avatars'),
                    fetch('/api/heygen/voices')
                ]);
                const avatarsData = await avatarsRes.json();
                const voicesData = await voicesRes.json();

                if (avatarsData.data?.avatars) setAvatars(avatarsData.data.avatars);
                if (voicesData.data?.voices) setVoices(voicesData.data.voices);
            } catch (e) {
                console.error("Failed to load config", e);
                toast.error("Failed to load avatars/voices");
            } finally {
                setLoadingConfig(false);
            }
        };
        fetchConfig();
    }, []);

    const supabase = createClient();
    const router = useRouter();

    const handleNext = () => setStep(step + 1);
    const handleBack = () => setStep(step - 1);
    const handleInput = (key: string, value: any) => setFormData((prev: any) => ({ ...prev, [key]: value }));

    const AMENITY_LIST = [
        'Swimming Pool', 'Gym', 'Clubhouse', 'Play Area',
        'CCTV', 'Security', 'Power Backup', 'Lift',
        'Parking', 'Garden'
    ];

    const handleAmenityChange = (amenity: string, checked: boolean) => {
        const currentString = formData.amenities || '';
        const newMap = new Map();
        AMENITY_LIST.forEach(a => {
            const isYes = currentString.includes(`${a}:Yes`);
            newMap.set(a, isYes);
        });
        newMap.set(amenity, checked);
        const newString = Array.from(newMap.entries())
            .map(([key, val]) => `${key}:${val ? 'Yes' : 'No'}`)
            .join(' | ');
        handleInput('amenities', newString);
    }

    const uploadMedia = async (key: string, file: File) => {
        if (!file) return;
        setUploadingState(prev => ({ ...prev, [key]: true }));
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error("User auth missing");
            const fileName = `${user.id}/${Date.now()}-${key}.${file.name.split('.').pop()}`;
            const { error } = await supabase.storage.from('video-assets').upload(fileName, file);
            if (error) throw error;
            const { data: { publicUrl } } = supabase.storage.from('video-assets').getPublicUrl(fileName);

            setFormData((prev: any) => ({
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
            toast.error("Please confirm the data.");
            return;
        }
        setGenerating(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) throw new Error("No user");

            const { data: property, error } = await supabase.from('video_properties').insert({
                user_id: user.id,
                title: `${formData.projectName} - ${formData.propertyType}`,
                description: `ID: ${formData.propertyId} | ${formData.city} | ${formData.category}`,
                details: formData
            }).select().single();

            if (error) throw error;


            let endpoint = '/api/heygen/generate';
            let payload: any = {
                propertyId: property.id,
                avatarId: formData.avatarId,
                voiceId: formData.voiceId,
                mediaUrls: formData.mediaUrls,
            };

            if (formData.category === 'Video Edit') {
                endpoint = '/api/creatomate/generate';
                // Construct modifications based on template
                const modifications = {
                    "fill_color": "#ffffff",
                    "Video-8P2.source": formData.mediaUrls['mainVideo'],
                    "Video-8P2.duration": "media",
                    "logo.source": formData.mediaUrls['mainImage'],
                    "logo.duration": null,
                    "Shape-R4V.duration": null,
                    "price-text.text": `${formData.propertyType || ''} from ${formData.priceLabel || ''}\nLimited Units`,
                    "price-text.duration": null,
                    "Text-R85.duration": null,
                    "Text-V22.text": `📍 ${formData.locality || ''} - ${formData.city || ''}`,
                    "Text-V22.duration": null,
                    "Text-V22.fill_color": "rgba(255,255,255,1)"
                };
                payload = {
                    propertyId: property.id,
                    modifications
                };
            }

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await res.json();
            if (!res.ok) throw new Error(result.error);

            toast.success("Success!");
            router.push(`/videos/${result.videoId}`);

        } catch (e: any) {
            toast.error(e.message);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="max-w-5xl mx-auto p-8 bg-card rounded-xl shadow-lg border my-10 animate-in fade-in slide-in-from-bottom-4">
            <div className="mb-8 border-b pb-4">
                <h2 className="text-3xl font-bold tracking-tight">Add New Property</h2>
                {step > 0 && (
                    <div className="flex gap-2 mt-4">
                        {[1, 2, 3, 4].map(s => (
                            <div key={s} className={`h-2 flex-1 rounded-full ${step >= s ? 'bg-primary' : 'bg-secondary'}`} />
                        ))}
                    </div>
                )}
                <p className="text-sm text-muted-foreground mt-2">
                    {step === 0 ? 'Select Category' : `Section ${step} / 4`}
                </p>
            </div>

            {step === 0 && (
                <div className="space-y-6 text-center py-8">
                    <h3 className="text-2xl font-semibold mb-8">What type of property is this?</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                            { id: 'Resale', label: 'Resale', desc: 'Existing properties for sale' },
                            { id: 'Rent', label: 'Rent / Lease', desc: 'Properties available for rent' },
                            { id: 'New Development', label: 'New Development', desc: 'Under construction or new launch projects' },
                            { id: 'Video Edit', label: 'Video Edit', desc: 'Upload video and details for custom edit' }
                        ].filter(c => !allowedCategories || allowedCategories.includes(c.id)).map((type) => (
                            <div
                                key={type.id}
                                className={`p-8 border-2 rounded-xl cursor-pointer hover:border-primary hover:bg-primary/5 transition-all flex flex-col items-center space-y-4 shadow-sm hover:shadow-md ${formData.category === type.id ? 'border-primary bg-primary/10 ring-2 ring-primary/20' : 'border-muted'}`}
                                onClick={() => {
                                    handleInput('category', type.id);
                                    setStep(1);
                                }}
                            >
                                <div className="h-14 w-14 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-2xl">
                                    {type.id[0]}
                                </div>
                                <div>
                                    <h4 className="font-bold text-xl">{type.label}</h4>
                                    <p className="text-sm text-muted-foreground mt-1">{type.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {step === 1 && (
                <div className="space-y-8 animate-in slide-in-from-right-8 fade-in duration-300">
                    {!forcedCategory && (
                        <div className="bg-primary/5 p-4 rounded-lg text-sm text-primary font-medium mb-4 flex justify-between items-center border border-primary/20">
                            <span className="flex items-center gap-2">
                                <span className="font-bold uppercase tracking-wider text-xs bg-primary text-white px-2 py-1 rounded">{formData.category}</span>
                                <span className="text-muted-foreground">Selected Category</span>
                            </span>
                            <Button variant="ghost" size="sm" onClick={() => setStep(0)} className="hover:bg-primary/10">Change</Button>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {formData.category !== 'Video Edit' && (
                            <>
                                <div>
                                    <Label className="text-primary font-bold">1. Property ID</Label>
                                    <Input placeholder="PUNE_3BHK_001" value={formData.propertyId} onChange={e => handleInput('propertyId', e.target.value)} />
                                </div>
                                <div>
                                    <Label className="text-primary font-bold">2. Project Name</Label>
                                    <Input placeholder="Godrej Green Vista" value={formData.projectName} onChange={e => handleInput('projectName', e.target.value)} />
                                </div>
                            </>
                        )}
                        <div>
                            <Label className="text-primary font-bold">{formData.category === 'Video Edit' ? '1. Configuration (e.g. 3 BHK)' : '3. Property Type'}</Label>
                            {formData.category === 'Video Edit' ? (
                                <Input placeholder="3 BHK" value={formData.propertyType} onChange={e => handleInput('propertyType', e.target.value)} />
                            ) : (
                                <select className="w-full h-10 rounded-md border border-input bg-background px-3" value={formData.propertyType} onChange={e => handleInput('propertyType', e.target.value)}>
                                    <option value="">Select Type</option>
                                    <option value="1 BHK Apartment">1 BHK Apartment</option>
                                    <option value="2 BHK Apartment">2 BHK Apartment</option>
                                    <option value="3 BHK Apartment">3 BHK Apartment</option>
                                    <option value="Villa">Villa</option>
                                    <option value="Row House">Row House</option>
                                </select>
                            )}
                        </div>
                        <div>
                            <Label className="text-primary font-bold">{formData.category === 'Video Edit' ? '2. City' : '4. City'}</Label>
                            <Input placeholder="Pune" value={formData.city} onChange={e => handleInput('city', e.target.value)} />
                        </div>
                        <div>
                            <Label className="text-primary font-bold">{formData.category === 'Video Edit' ? '3. Locality' : '5. Locality'}</Label>
                            <Input placeholder="Mahalunge" value={formData.locality} onChange={e => handleInput('locality', e.target.value)} />
                        </div>
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label className="text-primary font-bold">6. Builder / Developer</Label>
                                <Input placeholder="Godrej Properties" value={formData.builder} onChange={e => handleInput('builder', e.target.value)} />
                            </div>
                        )}
                        {formData.category === 'Video Edit' && (
                            // Phone input removed as it is fixed in template
                            null
                        )}
                    </div>

                    <div className="border-t pt-6 grid grid-cols-1 md:grid-cols-3 gap-6">
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label>7. Carpet Area (sq.ft)</Label>
                                <Input type="number" value={formData.carpetArea} onChange={e => handleInput('carpetArea', e.target.value)} />
                            </div>
                        )}
                        {formData.category !== 'Video Edit' && (
                            <>
                                <div>
                                    <Label>8. Floor</Label>
                                    <Input type="number" value={formData.floor} onChange={e => handleInput('floor', e.target.value)} />
                                </div>
                                <div>
                                    <Label>9. Total Floors</Label>
                                    <Input type="number" value={formData.totalFloors} onChange={e => handleInput('totalFloors', e.target.value)} />
                                </div>
                            </>
                        )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label>10. Furnishing Status</Label>
                                <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.furnishingStatus} onChange={e => handleInput('furnishingStatus', e.target.value)}>
                                    <option value="Unfurnished">Unfurnished</option>
                                    <option value="Semi-Furnished">Semi-Furnished</option>
                                    <option value="Fully Furnished">Fully Furnished</option>
                                </select>
                            </div>
                        )}
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label>11. Facing (Optional)</Label>
                                <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.facing} onChange={e => handleInput('facing', e.target.value)}>
                                    <option value="">Select</option>
                                    <option value="East">East</option>
                                    <option value="West">West</option>
                                    <option value="North">North</option>
                                    <option value="South">South</option>
                                </select>
                            </div>
                        )}
                    </div>

                    <div className="border-t pt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label>12. Price (INR Numeric)</Label>
                                <Input type="number" placeholder="9300000" value={formData.price} onChange={e => handleInput('price', e.target.value)} />
                            </div>
                        )}
                        <div>
                            <Label>{formData.category === 'Video Edit' ? '5. Price (e.g. ₹1.28 Cr)' : '13. Price Label (Display)'}</Label>
                            <Input placeholder="₹93 Lakhs" value={formData.priceLabel} onChange={e => handleInput('priceLabel', e.target.value)} />
                        </div>
                        {formData.category !== 'Video Edit' && (
                            <div>
                                <Label>14. Possession Status</Label>
                                <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.possessionStatus} onChange={e => handleInput('possessionStatus', e.target.value)}>
                                    <option value="">Select</option>
                                    <option value="Ready to Move">Ready to Move</option>
                                    <option value="Under Construction">Under Construction</option>
                                </select>
                            </div>
                        )}
                        {formData.category !== 'Video Edit' && (
                            <>
                                <div>
                                    <Label>15. Parking Details</Label>
                                    <Input placeholder="1 Covered" value={formData.parking} onChange={e => handleInput('parking', e.target.value)} />
                                </div>
                                <div>
                                    <Label>16. Availability</Label>
                                    <select className="w-full h-10 rounded-md border bg-background px-3" value={formData.availability} onChange={e => handleInput('availability', e.target.value)}>
                                        <option value="Available">Available</option>
                                        <option value="Sold">Sold</option>
                                        <option value="Hold">Hold</option>
                                    </select>
                                </div>
                            </>
                        )}
                    </div>

                    {formData.category !== 'Video Edit' && (
                        <div className="border-t pt-6">
                            <Label className="text-primary font-bold mb-4 block">17. Amenities</Label>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-y-4 gap-x-2">
                                {AMENITY_LIST.map(amenity => {
                                    const isChecked = formData.amenities?.includes(`${amenity}:Yes`);
                                    return (
                                        <div key={amenity} className="flex items-center space-x-2">
                                            <input
                                                type="checkbox"
                                                id={`chk-${amenity}`}
                                                checked={isChecked}
                                                onChange={(e) => handleAmenityChange(amenity, e.target.checked)}
                                                className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                            />
                                            <Label htmlFor={`chk-${amenity}`} className="font-normal cursor-pointer select-none">{amenity}</Label>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end pt-4">
                        <Button onClick={handleNext}>Next: Photos</Button>
                    </div>
                </div>
            )}

            {step === 2 && (
                <div className="space-y-6 animate-in slide-in-from-right-8 fade-in duration-300">
                    <h3 className="text-xl font-bold">Property Photos</h3>
                    <p className="text-sm text-yellow-600 bg-yellow-50 p-2 rounded">IMPORTANT: Upload high-quality horizontal images for best results.</p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {(formData.category === 'Video Edit' ? [
                            { key: 'mainVideo', label: 'Main Video (Upload Video)', type: 'video' },
                            { key: 'mainImage', label: 'Logo (Upload Image)', type: 'image' }
                        ] : [
                            { key: 'exterior', label: '18. Building / Exterior', type: 'image' },
                            { key: 'hall', label: '19. TV Hall / Living Room', type: 'image' },
                            { key: 'kitchen', label: '20. Kitchen', type: 'image' },
                            { key: 'bedroom', label: '21. Bedroom', type: 'image' },
                            { key: 'balcony', label: '22. Balcony / View (Optional)', type: 'image' },
                            { key: 'amenities', label: '23. Amenities (Optional)', type: 'image' }
                        ]
                        ).map((item: any) => (
                            <div key={item.key} className="border p-4 rounded-lg bg-muted/20">
                                <Label className="mb-2 block">{item.label}</Label>
                                {formData.mediaUrls[item.key] ? (
                                    <div className="relative h-40 w-full">
                                        {item.type === 'video' ? (
                                            <video src={formData.mediaUrls[item.key]} className="h-full w-full object-cover rounded" controls />
                                        ) : (
                                            <img src={formData.mediaUrls[item.key]} className="h-full w-full object-cover rounded" />
                                        )}
                                        <Button variant="destructive" size="icon" className="absolute top-1 right-1 h-6 w-6" onClick={() => {
                                            const newUrls = { ...formData.mediaUrls };
                                            delete newUrls[item.key];
                                            handleInput('mediaUrls', newUrls);
                                        }}>x</Button>
                                    </div>
                                ) : (
                                    <div className="flex items-center justify-center p-6 border-2 border-dashed rounded cursor-pointer hover:bg-muted" onClick={() => document.getElementById(`file-${item.key}`)?.click()}>
                                        {uploadingState[item.key] ? 'Uploading...' : `Upload ${item.type === 'video' ? 'Video' : 'Image'}`}
                                        <input
                                            id={`file-${item.key}`}
                                            type="file"
                                            className="hidden"
                                            accept={item.type === 'video' ? "video/*" : "image/*"}
                                            onChange={e => e.target.files && uploadMedia(item.key, e.target.files[0])}
                                        />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between pt-6">
                        <Button variant="outline" onClick={handleBack}>Back</Button>
                        <Button onClick={handleNext}>Next: Configuration</Button>
                    </div>
                </div>
            )}

            {step === 3 && (
                <div className="space-y-6 animate-in slide-in-from-right-8 fade-in duration-300">
                    <h3 className="text-xl font-bold">Configuration</h3>
                    {formData.category === 'Video Edit' ? (
                        <div className="text-center py-20 bg-muted/20 rounded border-dashed border-2">
                            <h4 className="text-xl font-semibold mb-2">Ready for Rendering</h4>
                            <p className="text-muted-foreground">This template does not require avatar or voice configuration.</p>
                        </div>
                    ) : (
                        <>
                            <h3 className="text-lg font-bold mb-4">Avatar & Voice Configuration</h3>
                            {loadingConfig ? (
                                <div className="text-center py-10">Loading configuration options...</div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div>
                                        <Label>24. Select Avatar</Label>
                                        <div className="grid grid-cols-2 gap-4 max-h-[400px] overflow-y-auto mt-2 border rounded p-2">
                                            {avatars.map((avatar: any) => (
                                                <div
                                                    key={avatar.avatar_id}
                                                    className={`p-2 border rounded cursor-pointer hover:bg-primary/5 flex flex-col items-center gap-2 ${formData.avatarId === avatar.avatar_id ? 'border-primary ring-2 ring-primary/20 bg-primary/10' : ''}`}
                                                    onClick={() => handleInput('avatarId', avatar.avatar_id)}
                                                >
                                                    <div className="w-16 h-16 rounded-full overflow-hidden bg-gray-200">
                                                        {avatar.preview_image_url ? (
                                                            <img src={avatar.preview_image_url} alt={avatar.avatar_name} className="w-full h-full object-cover" />
                                                        ) : (
                                                            <div className="w-full h-full flex items-center justify-center text-xs">No Img</div>
                                                        )}
                                                    </div>
                                                    <span className="text-xs text-center font-medium truncate w-full">{avatar.avatar_name || avatar.avatar_id}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    <div>
                                        <Label>25. Select Voice</Label>
                                        <div className="space-y-2 max-h-[400px] overflow-y-auto mt-2 border rounded p-2">
                                            {voices.length > 0 ? voices.map((voice: any) => (
                                                <div
                                                    key={voice.voice_id}
                                                    className={`p-3 border rounded cursor-pointer hover:bg-primary/5 text-sm flex justify-between items-center ${formData.voiceId === voice.voice_id ? 'border-primary ring-2 ring-primary/20 bg-primary/10' : ''}`}
                                                    onClick={() => handleInput('voiceId', voice.voice_id)}
                                                >
                                                    <span className="font-medium">{voice.name}</span>
                                                    <span className="text-xs text-muted-foreground">{voice.language} {voice.gender}</span>
                                                </div>
                                            )) : (
                                                <div className="p-4 text-center text-muted-foreground">No voices found</div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                    <div className="flex justify-between pt-6">
                        <Button variant="outline" onClick={handleBack}>Back</Button>
                        <Button onClick={handleNext} disabled={formData.category !== 'Video Edit' && (!formData.avatarId || !formData.voiceId)}>Next: Review</Button>
                    </div>
                </div>
            )}

            {step === 4 && (
                <div className="space-y-6 animate-in slide-in-from-right-8 fade-in duration-300">
                    <h3 className="text-xl font-bold">Review & Submit</h3>
                    <div className="bg-slate-50 p-6 rounded-lg text-sm space-y-2">
                        <p><strong>Category:</strong> {formData.category}</p>
                        <p><strong>Project:</strong> {formData.projectName}</p>
                        <p><strong>Type:</strong> {formData.propertyType}</p>
                        <p><strong>Price:</strong> {formData.priceLabel}</p>
                        <p><strong>Photos:</strong> {Object.keys(formData.mediaUrls).length} Uploaded</p>
                        <p><strong>Config:</strong> {formData.category === 'Video Edit' ? 'Template Based' : `Avatar: ${formData.avatarId}, Voice: ${formData.voiceId}`}</p>
                    </div>

                    <div className="flex items-center space-x-2 border p-4 rounded bg-blue-50">
                        <input
                            type="checkbox"
                            id="consent"
                            checked={formData.confirmed}
                            onChange={e => handleInput('confirmed', e.target.checked)}
                            className="h-4 w-4"
                        />
                        <label htmlFor="consent" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                            I confirm that the above information and images are accurate and authorized for marketing use.
                        </label>
                    </div>

                    <div className="flex justify-between pt-6">
                        <Button variant="outline" onClick={handleBack} disabled={generating}>Back</Button>
                        <Button onClick={handleGenerate} disabled={!formData.confirmed || generating} className="w-40">
                            {generating ? 'Processing...' : 'Generate Video'}
                        </Button>
                    </div>
                </div>
            )}

        </div>
    );
}
