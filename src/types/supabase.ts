export type Json =
    | string
    | number
    | boolean
    | null
    | { [key: string]: Json | undefined }
    | Json[]

export interface Database {
    public: {
        Tables: {
            video_properties: {
                Row: {
                    id: string
                    user_id: string
                    title: string
                    category: string | null
                    description: string | null
                    address_city: string | null
                    specs: Json | null
                    created_at: string
                    updated_at: string
                }
                Insert: {
                    id?: string
                    user_id?: string
                    title: string
                    category?: string | null
                    description?: string | null
                    address_city?: string | null
                    specs?: Json | null
                    created_at?: string
                    updated_at?: string
                }
                Update: {
                    id?: string
                    user_id?: string
                    title?: string
                    category?: string | null
                    description?: string | null
                    address_city?: string | null
                    specs?: Json | null
                    created_at?: string
                    updated_at?: string
                }
            }
            video_media: {
                Row: {
                    id: string
                    property_id: string
                    user_id: string
                    storage_path: string
                    public_url: string
                    mime_type: string | null
                    order: number
                    created_at: string
                }
                Insert: {
                    id?: string
                    property_id: string
                    user_id: string
                    storage_path: string
                    public_url: string
                    mime_type?: string | null
                    order?: number
                    created_at?: string
                }
                Update: {
                    id?: string
                    property_id?: string
                    user_id?: string
                    storage_path?: string
                    public_url?: string
                    mime_type?: string | null
                    order?: number
                    created_at?: string
                }
            }
            videos: {
                Row: {
                    id: string
                    user_id: string
                    property_id: string
                    title: string | null
                    script_content: string | null
                    avatar_id: string | null
                    voice_id: string | null
                    purpose: 'sale' | 'rent' | null
                    status: 'draft' | 'pending' | 'processing' | 'completed' | 'failed' | null
                    heygen_video_id: string | null
                    video_url: string | null
                    thumbnail_url: string | null
                    error_message: string | null
                    meta: Json | null
                    created_at: string
                    updated_at: string
                }
                Insert: {
                    id?: string
                    user_id: string
                    property_id: string
                    title?: string | null
                    script_content?: string | null
                    avatar_id?: string | null
                    voice_id?: string | null
                    purpose?: 'sale' | 'rent' | null
                    status?: 'draft' | 'pending' | 'processing' | 'completed' | 'failed' | null
                    heygen_video_id?: string | null
                    video_url?: string | null
                    thumbnail_url?: string | null
                    error_message?: string | null
                    meta?: Json | null
                    created_at?: string
                    updated_at?: string
                }
                Update: {
                    id?: string
                    user_id?: string
                    property_id?: string
                    title?: string | null
                    script_content?: string | null
                    avatar_id?: string | null
                    voice_id?: string | null
                    purpose?: 'sale' | 'rent' | null
                    status?: 'draft' | 'pending' | 'processing' | 'completed' | 'failed' | null
                    heygen_video_id?: string | null
                    video_url?: string | null
                    thumbnail_url?: string | null
                    error_message?: string | null
                    meta?: Json | null
                    created_at?: string
                    updated_at?: string
                }
            }
        }
    }
}
