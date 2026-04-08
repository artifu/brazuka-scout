-- enable_rls.sql
-- Enable Row-Level Security on all public tables and add read-only policy
-- for the anon role (used by the dashboard via NEXT_PUBLIC_SUPABASE_ANON_KEY).
-- Writes are done exclusively via the service role key, which bypasses RLS.

-- ── Enable RLS ────────────────────────────────────────────────────────────────
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

-- ── Read-only policies for anon role (dashboard reads) ────────────────────────
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

-- No INSERT/UPDATE/DELETE policies for anon → only service role can write.
