import { getAvatars } from '@/lib/heygen/client';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const data = await getAvatars();
        return NextResponse.json(data);
    } catch (error: any) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}
