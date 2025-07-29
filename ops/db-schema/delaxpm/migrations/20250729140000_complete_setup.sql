/*
  # Complete Database Setup
  
  1. Calendar Events Table
  2. Team Dashboard Data Initialization
  3. Handle all existing conflicts
*/

-- =========================================
-- PART 1: Calendar Events Table
-- =========================================

-- Create calendar_events table
CREATE TABLE IF NOT EXISTS calendar_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  episode_id bigint REFERENCES episodes(id) ON DELETE SET NULL,
  task_type text NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  meeting_url text,
  description text,
  is_team_event boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  
  -- Date validation
  CONSTRAINT valid_date_range CHECK (end_date >= start_date),
  -- Meeting URL validation
  CONSTRAINT valid_meeting_url CHECK (meeting_url IS NULL OR meeting_url ~ '^https?://')
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_calendar_events_dates ON calendar_events (start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_calendar_events_episode_id ON calendar_events (episode_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_team_event ON calendar_events (is_team_event);
CREATE INDEX IF NOT EXISTS idx_calendar_events_task_type ON calendar_events (task_type);

-- Enable RLS
ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist and create new ones
DO $$ 
BEGIN
  DROP POLICY IF EXISTS "Enable read access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable insert access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable update access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable delete access for all users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable read access for authenticated users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable update access for authenticated users" ON calendar_events;
  DROP POLICY IF EXISTS "Enable delete access for authenticated users" ON calendar_events;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

-- Create policies for authenticated users
CREATE POLICY "Enable read access for authenticated users" ON calendar_events
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON calendar_events
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON calendar_events
  FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "Enable delete access for authenticated users" ON calendar_events
  FOR DELETE TO authenticated USING (true);

-- Create updated_at trigger function and trigger
CREATE OR REPLACE FUNCTION update_calendar_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_calendar_events_updated_at ON calendar_events;
CREATE TRIGGER update_calendar_events_updated_at
  BEFORE UPDATE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION update_calendar_events_updated_at();

-- =========================================
-- PART 2: Reserved for future team features
-- =========================================

-- This section is reserved for future team-related functionality

-- =========================================
-- PART 3: Verification
-- =========================================

-- Verify table creation
DO $$
DECLARE
    calendar_table_exists BOOLEAN;
BEGIN
    -- Check if calendar_events table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'calendar_events'
    ) INTO calendar_table_exists;
    
    -- Report results
    RAISE NOTICE 'Setup verification:';
    RAISE NOTICE '- Calendar events table exists: %', calendar_table_exists;
    
    IF calendar_table_exists THEN
        RAISE NOTICE 'Calendar events setup completed successfully!';
    ELSE
        RAISE WARNING 'Calendar events setup may have issues - please verify manually';
    END IF;
END $$;