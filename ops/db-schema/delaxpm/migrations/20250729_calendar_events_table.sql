/*
  # Calendar Events Table Creation
  
  1. New Table
    - `calendar_events` - Calendar events and tasks management
    
  2. Features
    - Support for episode-related tasks
    - Support for team events with meeting URLs
    - Comprehensive task and event management
    - Guest access compatibility
    
  3. Schema
    - Compatible with existing CalendarEvent interface
    - Extended from temp_liberary calendar_tasks structure
*/

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

-- Create policies for guest access (full CRUD permissions)
CREATE POLICY "Enable read access for all users" ON calendar_events
  FOR SELECT USING (true);

CREATE POLICY "Enable insert access for all users" ON calendar_events
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update access for all users" ON calendar_events
  FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Enable delete access for all users" ON calendar_events
  FOR DELETE USING (true);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_calendar_events_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_calendar_events_updated_at
  BEFORE UPDATE ON calendar_events
  FOR EACH ROW
  EXECUTE FUNCTION update_calendar_events_updated_at();

-- Add comments for documentation
COMMENT ON TABLE calendar_events IS 'Calendar events and tasks for episode management and team coordination';
COMMENT ON COLUMN calendar_events.episode_id IS 'Reference to episodes table for episode-related tasks';
COMMENT ON COLUMN calendar_events.task_type IS 'Type of task or event (編集, 試写, MA, etc.)';
COMMENT ON COLUMN calendar_events.meeting_url IS 'Web meeting URL for team events';
COMMENT ON COLUMN calendar_events.description IS 'Additional details and notes';
COMMENT ON COLUMN calendar_events.is_team_event IS 'Flag to distinguish team events from episode tasks';