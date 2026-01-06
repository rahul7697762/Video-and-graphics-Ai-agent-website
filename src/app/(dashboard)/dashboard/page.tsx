import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function DashboardPage() {
    return (
        <div className="space-y-8">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
                <div className="flex items-center space-x-2">
                    <Link href="/properties/new">
                        <Button>Create New Video</Button>
                    </Link>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                    <h3 className="tracking-tight text-sm font-medium">Total Videos</h3>
                    <div className="text-2xl font-bold">0</div>
                </div>
                <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                    <h3 className="tracking-tight text-sm font-medium">Generating</h3>
                    <div className="text-2xl font-bold">0</div>
                </div>
                <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                    <h3 className="tracking-tight text-sm font-medium">Ad Spend</h3>
                    <div className="text-2xl font-bold">$0.00</div>
                </div>
                <div className="rounded-xl border bg-card text-card-foreground shadow p-6">
                    <h3 className="tracking-tight text-sm font-medium">Leads</h3>
                    <div className="text-2xl font-bold">0</div>
                </div>
            </div>

            <div className="rounded-xl border bg-card text-card-foreground shadow p-6 min-h-[300px] flex items-center justify-center text-muted-foreground">
                Analytics Charts Placeholder
            </div>
        </div>
    );
}
