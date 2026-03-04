import { createClient as createSupabaseClient } from '@supabase/supabase-js';

const SUPABASE_URL = 'https://gpczchjipalfgkfqamcu.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwY3pjaGppcGFsZmdrZnFhbWN1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgwNzgxMjIsImV4cCI6MjA3MzY1NDEyMn0.MCPjoXNNdtFmGjvDKVFxFXi5ff-0Lp366nkVOkEBWa8';

let client: ReturnType<typeof createSupabaseClient> | null = null;

export function getSupabaseClient() {
  if (!client) {
    client = createSupabaseClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: { persistSession: true, autoRefreshToken: true },
    });
  }
  return client;
}

export async function signOut() {
  const supabase = getSupabaseClient();
  await supabase.auth.signOut();
  const landingUrl = import.meta.env.PROD
    ? 'https://neufinfinalbuild1.vercel.app/'
    : 'http://localhost:3000/';
  window.location.replace(landingUrl);
}
