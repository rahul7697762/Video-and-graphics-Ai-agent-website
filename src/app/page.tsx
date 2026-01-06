import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Home() {
    return (
        <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-b from-background to-muted">
            <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex mb-10">
                <p className="fixed left-0 top-0 flex w-full justify-center border-b bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
                    Real Estate Video Automation
                </p>
            </div>

            <div className="text-center space-y-6 max-w-2xl">
                <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
                    Turn Property Listings into <span className="text-primary">AI Videos</span>
                </h1>
                <p className="text-xl text-muted-foreground">
                    Generate professional, avatar-presented videos for your real estate properties in minutes using HeyGen AI.
                </p>
                <div className="flex gap-4 justify-center pt-4">
                    <Link href="/login">
                        <Button size="lg">Login to Dashboard</Button>
                    </Link>
                    <Link href="/register">
                        <Button variant="outline" size="lg">Create Account</Button>
                    </Link>
                </div>
            </div>
        </main>
    );
}
