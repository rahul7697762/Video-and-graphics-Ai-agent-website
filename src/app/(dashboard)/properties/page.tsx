import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default async function PropertiesPage() {
    const supabase = createClient();
    const { data: { user } } = await supabase.auth.getUser();

    const { data: properties } = await supabase
        .from('video_properties')
        .select('*')
        .eq('user_id', user?.id || '')
        .order('created_at', { ascending: false });

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold">My Properties</h1>
                <Link href="/properties/new">
                    <Button>+ Add Property</Button>
                </Link>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {properties?.map((property: any) => (
                    <div key={property.id} className="border rounded-lg p-4 shadow-sm bg-card hover:shadow-md transition-shadow">
                        <h3 className="font-semibold text-lg truncate">{property.title}</h3>
                        <p className="text-sm text-muted-foreground line-clamp-2 mt-2">{property.description}</p>
                        <div className="mt-4 pt-4 border-t flex justify-between items-center text-sm">
                            <span className="text-muted-foreground">{new Date(property.created_at).toLocaleDateString()}</span>
                            <Button variant="ghost" size="sm">View</Button>
                        </div>
                    </div>
                ))}
                {(!properties || properties.length === 0) && (
                    <div className="col-span-full text-center py-10 bg-muted/20 rounded-lg border-dashed border-2">
                        <p className="text-muted-foreground mb-4">No properties found.</p>
                        <Link href="/properties/new"><Button variant="outline">Create your first property</Button></Link>
                    </div>
                )}
            </div>
        </div>
    );
}
