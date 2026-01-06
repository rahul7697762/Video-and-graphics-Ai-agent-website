# Real Estate Video Automation Platform - Architecture (Supabase Edition)

## 1. Project Overview

A comprehensive platform for real estate teams to generate AI-presented property videos using HeyGen, with full analytics and ad performance tracking, built on Supabase.

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), TypeScript, TailwindCSS, shadcn/ui |
| State | React Server Components + Client Components |
| Charts | Recharts |
| Backend | Next.js API Routes (Server Actions preferred) |
| Database | Supabase PostgreSQL |
| Auth | Supabase Auth (RBAC: Admin / User) |
| Storage | Supabase Storage |
| Video Engine | HeyGen API v2 |

## 3. Folder Structure

```
real_state_project/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── check-email/page.tsx
│   │   └── callback/route.ts        # Auth callback
│   ├── (dashboard)/
│   │   ├── dashboard/page.tsx
│   │   ├── properties/
│   │   │   ├── page.tsx
│   │   │   ├── [id]/page.tsx
│   │   │   └── new/page.tsx         # Multi-step Wizard
│   │   ├── videos/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx
│   │   ├── analytics/page.tsx
│   │   ├── ad-performance/page.tsx
│   │   └── layout.tsx
│   ├── api/
│   │   ├── heygen/
│   │   │   ├── generate/route.ts    # Webhook target or server-side trigger
│   │   │   └── webhook/route.ts     # Listen for HeyGen completion
│   │   └── cron/
│   │       └── sync-status/route.ts # Fallback status polling
│   ├── layout.tsx
│   ├── error.tsx
│   └── page.tsx
├── components/
│   ├── ui/                          # shadcn/ui
│   ├── auth/                        # Auth forms
│   ├── dashboard/                   # Shell, Sidebar, Header
│   ├── wizard/                      # Property/Video Wizard Steps
│   ├── video/                       # Player, Status badges
│   └── charts/                      # Recharts wrappers
├── lib/
│   ├── supabase/
│   │   ├── server.ts                # SSR client
│   │   ├── client.ts                # Browser client
│   │   └── admin.ts                 # Admin client (service_role)
│   ├── heygen/
│   │   ├── client.ts                # HeyGen API wrapper
│   │   └── templates.ts             # Script templates
│   ├── utils.ts
│   └── validations/                 # Zod schemas
├── types/
│   ├── supabase.ts                  # Generated DB types
│   └── index.ts                     # App-specific types
├── supabase/
│   ├── migrations/                  # SQL migrations
│   └── seed.sql                     # Initial data
├── .env.local
└── next.config.js
```

## 4. Supabase Database Schema

### Users (profiles) - Extends Supabase Auth
```sql
create type user_role as enum ('admin', 'user');

create table profiles (
  id uuid references auth.users not null primary key,
  email text,
  full_name text,
  role user_role default 'user',
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### Properties
```sql
create type property_category as enum ('residential', 'commercial', 'resale');

create table properties (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references profiles(id) not null,
  title text not null,
  description text,
  category property_category not null,
  address jsonb, -- { street, city, state, zip }
  specs jsonb,   -- { price, area, beds, baths, amenities: [] }
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### Property Media
```sql
create table property_media (
  id uuid default gen_random_uuid() primary key,
  property_id uuid references properties(id) on delete cascade not null,
  user_id uuid references profiles(id) not null,
  storage_path text not null,
  public_url text not null,
  mime_type text,
  "order" int default 0,
  created_at timestamptz default now()
);
```

### Videos
```sql
create type video_status as enum ('draft', 'pending', 'processing', 'completed', 'failed');
create type video_purpose as enum ('sale', 'rent');

create table videos (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references profiles(id) not null,
  property_id uuid references properties(id) not null,
  title text,
  script_content text,
  avatar_id text,
  voice_id text,
  purpose video_purpose default 'sale',
  status video_status default 'draft',
  heygen_video_id text,
  video_url text,           -- Final HeyGen URL or self-hosted copy
  thumbnail_url text,
  error_message text,
  meta jsonb,               -- { duration, dimension, aspect_ratio }
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### Video Render Jobs (Audit Log)
```sql
create table video_render_jobs (
  id uuid default gen_random_uuid() primary key,
  video_id uuid references videos(id) on delete cascade,
  heygen_job_id text,
  status text,
  attempt_count int default 1,
  started_at timestamptz default now(),
  completed_at timestamptz,
  cost_credits float -- tracked cost
);
```

### Ad Performance
```sql
create type ad_platform as enum ('meta', 'google', 'youtube', 'manual');

create table ad_performance (
  id uuid default gen_random_uuid() primary key,
  video_id uuid references videos(id),
  user_id uuid references profiles(id),
  platform ad_platform not null,
  spend_amount numeric(10,2) default 0,
  impressions int default 0,
  clicks int default 0,
  leads int default 0,
  date_recorded date default current_date,
  created_at timestamptz default now()
);
```

## 5. Security (RLS)

- **Profiles**: Users can read own; Admin can read all.
- **Properties/Videos**: Users can CRUD their own records.
- **Storage**:
  - `property-images`: Public read, Authenticated upload (owner only).
  - `generated-videos`: Public read, Authenticated upload (system/owner).

## 6. HeyGen Integration Flow

1.  **Frontend**: User selects Property + Avatar -> "Generate"
2.  **Server Action**:
    *   Construct script (GPT or Template).
    *   Call HeyGen API (`POST /v2/video/generate`).
    *   Create `videos` record with status `pending`.
3.  **Status Tracking**:
    *   **Option A (Webhook)**: HeyGen calls `/api/heygen/webhook` -> updates DB.
    *   **Option B (Polling)**: Client polls internal API -> internal API checks HeyGen -> updates DB.
4.  **Completion**:
    *   Video marked `completed`.
    *   URL saved to DB.
    *   (Optional) Download video to Supabase Storage for permanence.

## 7. Analytics Logic

- **CPL (Cost Per Lead)**: `SUM(spend_amount) / SUM(leads)`
- **Usage Cost**: `SUM(cost_credits)` from render jobs.
- **Success Rate**: `COUNT(status='completed') / COUNT(all_videos)`

## 8. Environment Variables

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=... # For admin tasks/webhooks

HEYGEN_API_KEY=...
HEYGEN_WEBHOOK_SECRET=...
```
