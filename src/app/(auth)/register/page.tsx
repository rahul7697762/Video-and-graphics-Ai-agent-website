'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import Link from 'next/link';

export default function RegisterPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const router = useRouter();
    const supabase = createClient();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        const { error } = await supabase.auth.signUp({
            email,
            password,
        });

        if (error) {
            toast.error(error.message);
            setLoading(false);
        } else {
            toast.success('Registration successful! Please check your email.');
            // Optional: Auto redirect if session is established or asking to verify
            router.push('/login');
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center p-4">
            <div className="w-full max-w-sm space-y-6 rounded-lg border p-6 shadow-md bg-card">
                <div className="space-y-2 text-center">
                    <h1 className="text-2xl font-bold">Register</h1>
                    <p className="text-muted-foreground">Create an account to start</p>
                </div>
                <form onSubmit={handleRegister} className="space-y-4">
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
                            min={6}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? 'Creating...' : 'Register'}
                    </Button>
                </form>
                <div className="text-center text-sm">
                    Already have an account?{' '}
                    <Link href="/login" className="text-primary hover:underline">
                        Login
                    </Link>
                </div>
            </div>
        </div>
    );
}
