-- Add league_position to seasons table
-- Run once in Supabase SQL editor, then manually set position per season
ALTER TABLE seasons ADD COLUMN IF NOT EXISTS league_position integer;
