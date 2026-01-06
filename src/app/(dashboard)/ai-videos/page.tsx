import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default async function AIVideosPage() {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    const { data: allVideos } = await supabase
        .from('videos')
        .select('*, video_properties(title)')
        .eq('user_id', user?.id || '')
        .order('created_at', { ascending: false });

    // Filter for AI Videos (HeyGen)
    const videos = allVideos?.filter((v: any) => v.meta?.template !== 'CREATOMATE_EDIT');

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold">AI Videos</h1>
                    <p className="text-muted-foreground">Generated with HeyGen Avatars</p>
                </div>
                <Link href="/ai-videos/new">
                    <Button>+ New AI Video</Button>
                </Link>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {videos?.map((video: any) => (
                    <Link key={video.id} href={`/videos/${video.id}`} className="block group">
                        <div className="border rounded-lg overflow-hidden shadow-sm bg-card group-hover:shadow-md transition-all">
                            <div className="aspect-video bg-muted flex items-center justify-center relative">
                                {video.thumbnail_url ? (
                                    <img src={video.thumbnail_url} alt={video.title} className="w-full h-full object-cover" />
                                ) : (
                                    <div className="text-muted-foreground text-sm capitalize">
                                        {video.status === 'completed' ? 'Preview' : video.status}
                                    </div>
                                )}
                                <div className={`absolute top-2 right-2 px-2 py-1 text-white text-xs rounded uppercase font-bold ${video.status === 'completed' ? 'bg-green-600' : 'bg-yellow-600'}`}>
                                    {video.status}
                                </div>
                            </div>
                            <div className="p-4">
                                <h3 className="font-semibold text-lg truncate">{video.title || video.video_properties?.title || 'Untitled Video'}</h3>
                                <p className="text-xs text-muted-foreground mt-1">Generated: {new Date(video.created_at).toLocaleDateString()}</p>
                            </div>
                        </div>
                    </Link>
                ))}
                {(!videos || videos.length === 0) && (
                    <div className="col-span-full text-center py-10 bg-muted/20 rounded-lg border-dashed border-2">
                        <p className="text-muted-foreground mb-4">No AI videos generated yet.</p>
                        <Link href="/ai-videos/new"><Button variant="outline">Create your first AI video</Button></Link>
                    </div>
                )}
            </div>
        </div>
    );
}
