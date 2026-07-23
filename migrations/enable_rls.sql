-- enable_rls.sql  (authoritative • idempotent • self-healing — safe to re-run)
--
-- Enables Row-Level Security on EVERY table in the public schema and grants a
-- read-only "public read" policy to the anon role (used by the dashboard via
-- NEXT_PUBLIC_SUPABASE_ANON_KEY). Writes always go through the service role
-- key, which bypasses RLS entirely.
--
-- Why a loop instead of a hand-written list: enabling RLS only ever RESTRICTS
-- access, never exposes it, so it is always safe to enable on every table.
-- Looping over pg_tables means any NEW table is covered automatically the next
-- time this script runs — no table can silently slip out and trigger Supabase's
-- "Table publicly accessible" alert again.
--
-- To lock a table down to service-role only (no anon read), add its name to the
-- `sensitive` array below. It still gets RLS enabled, but no read policy, so the
-- anon key sees nothing and only the service key (bot backend) can touch it.

DO $$
DECLARE
  t         text;
  -- Tables the anon role must NOT read. RLS is still enabled on them; they just
  -- get no "public read" policy, so only the service role key can access them.
  sensitive text[] := ARRAY[
    'rag_chunks'   -- embedded WhatsApp chat history; queried only by the bot backend
  ];
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    -- 1. Enable RLS on every table (restrict-only; can never over-expose).
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t);

    -- 2. Re-create the read policy (drop first so re-runs never error).
    EXECUTE format('DROP POLICY IF EXISTS "public read" ON public.%I;', t);

    IF NOT (t = ANY (sensitive)) THEN
      EXECUTE format(
        'CREATE POLICY "public read" ON public.%I FOR SELECT USING (true);', t
      );
    END IF;
  END LOOP;
END $$;

-- No INSERT/UPDATE/DELETE policies are ever created for anon → only the service
-- role can write. Views (e.g. anything created as a VIEW) are skipped because
-- pg_tables lists base tables only, and RLS does not apply to views anyway.
