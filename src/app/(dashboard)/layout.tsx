import Link from "next/link";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex min-h-screen">
            <aside className="w-64 border-r bg-muted/40 hidden md:block">
                <div className="p-6 font-bold text-xl">RealEstate AI</div>
                <nav className="p-4 space-y-2">
                    <Link href="/dashboard" className="block p-2 hover:bg-accent rounded">Dashboard</Link>
                    <Link href="/properties" className="block p-2 hover:bg-accent rounded">Properties</Link>
                    <Link href="/ai-videos" className="block p-2 hover:bg-accent rounded">AI Video</Link>
                    <Link href="/custom-videos" className="block p-2 hover:bg-accent rounded">Custom Videos</Link>
                    <Link href="/graphic-designer" className="block p-2 hover:bg-accent rounded font-medium text-primary bg-accent/10">Graphic Designer</Link>
                    <Link href="/analytics" className="block p-2 hover:bg-accent rounded">Analytics</Link>
                </nav>
            </aside>
            <main className="flex-1">
                <header className="h-16 border-b flex items-center px-6">
                    <h1 className="font-semibold">Dashboard</h1>
                </header>
                <div className="p-6">
                    {children}
                </div>
            </main>
        </div>
    )
}
