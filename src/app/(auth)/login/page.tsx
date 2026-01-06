'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import Link from 'next/link';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const supabase = createClient();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });

        if (error) {
            toast.error(error.message);
            setLoading(false);
        } else {
            toast.success('LoggedIn successfully!');
            router.push('/dashboard');
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="w-full max-w-sm space-y-6 rounded-lg border p-6 shadow-md bg-card">
                <div className="space-y-2 text-center">
                    <h1 className="text-2xl font-bold">Login</h1>
                    <p className="text-muted-foreground">Welcome back to the platform</p>
                </div>
                <form onSubmit={handleLogin} className="space-y-4">
                    <div className="space-y-2">
                        <Input
                            type="email"
                            placeholder="Email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>
                    <div className="space-y-2">
                        <Input
                            type="password"
                            placeholder="Password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? 'Logging in...' : 'Login'}
                    </Button>
                </form>
                <div className="text-center text-sm">
                    Don&apos;t have an account?{' '}
                    <Link href="/register" className="text-primary hover:underline">
                        Register
                    </Link>
                </div>
            </div>
        </div>
    );
}
