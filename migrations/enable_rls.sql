-- enable_rls.sql  (safe to re-run — idempotent)
-- Enable Row-Level Security on ALL public tables and add read-only policy
-- for the anon role (used by the dashboard via NEXT_PUBLIC_SUPABASE_ANON_KEY).
-- Writes are done exclusively via the service role key, which bypasses RLS.

-- ── Enable RLS (idempotent) ────────────────────────────────────────────────
ALTER TABLE public.games          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.goals          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assists        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appearances    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.players        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teams          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seasons        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.division_games ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.elo_ratings    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_impact  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.badges         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.game_players   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.player_badges  ENABLE ROW LEVEL SECURITY;

-- ── Read-only policies (drop first so re-runs don't error) ─────────────────
DROP POLICY IF EXISTS "public read" ON public.games;
DROP POLICY IF EXISTS "public read" ON public.goals;
DROP POLICY IF EXISTS "public read" ON public.assists;
DROP POLICY IF EXISTS "public read" ON public.appearances;
DROP POLICY IF EXISTS "public read" ON public.players;
DROP POLICY IF EXISTS "public read" ON public.teams;
DROP POLICY IF EXISTS "public read" ON public.seasons;
DROP POLICY IF EXISTS "public read" ON public.division_games;
DROP POLICY IF EXISTS "public read" ON public.elo_ratings;
DROP POLICY IF EXISTS "public read" ON public.player_impact;
DROP POLICY IF EXISTS "public read" ON public.predictions;
DROP POLICY IF EXISTS "public read" ON public.badges;
DROP POLICY IF EXISTS "public read" ON public.game_players;
DROP POLICY IF EXISTS "public read" ON public.player_badges;

CREATE POLICY "public read" ON public.games          FOR SELECT USING (true);
CREATE POLICY "public read" ON public.goals          FOR SELECT USING (true);
CREATE POLICY "public read" ON public.assists        FOR SELECT USING (true);
CREATE POLICY "public read" ON public.appearances    FOR SELECT USING (true);
CREATE POLICY "public read" ON public.players        FOR SELECT USING (true);
CREATE POLICY "public read" ON public.teams          FOR SELECT USING (true);
CREATE POLICY "public read" ON public.seasons        FOR SELECT USING (true);
CREATE POLICY "public read" ON public.division_games FOR SELECT USING (true);
CREATE POLICY "public read" ON public.elo_ratings    FOR SELECT USING (true);
CREATE POLICY "public read" ON public.player_impact  FOR SELECT USING (true);
CREATE POLICY "public read" ON public.predictions    FOR SELECT USING (true);
CREATE POLICY "public read" ON public.badges         FOR SELECT USING (true);
CREATE POLICY "public read" ON public.game_players   FOR SELECT USING (true);
CREATE POLICY "public read" ON public.player_badges  FOR SELECT USING (true);

-- No INSERT/UPDATE/DELETE policies for anon → only service role can write.
