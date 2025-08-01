/*
  # Add team events functionality to calendar_tasks
  
  1. Changes
    - Add `meeting_url` text field (nullable) - for web meeting URLs
    - Add `description` text field (nullable) - for event details
    - Add `is_team_event` boolean field (default false) - to distinguish team events
  
  2. Features
    - Support for web meetings with URLs (全体会議, 制作会議)
    - Support for studio recordings (スタジオ収録)
    - Enhanced filtering capabilities
*/

-- Add new columns to calendar_tasks table
ALTER TABLE calendar_tasks 
  ADD COLUMN IF NOT EXISTS meeting_url text,
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS is_team_event boolean DEFAULT false;

-- Add constraint for meeting URL format (basic validation)
ALTER TABLE calendar_tasks 
  ADD CONSTRAINT valid_meeting_url 
  CHECK (meeting_url IS NULL OR meeting_url ~ '^https?://');

-- Add index for better query performance on team events
CREATE INDEX IF NOT EXISTS idx_calendar_tasks_team_event ON calendar_tasks (is_team_event);

-- Add comment for documentation
COMMENT ON COLUMN calendar_tasks.meeting_url IS 'Web meeting URL for 全体会議 and 制作会議';
COMMENT ON COLUMN calendar_tasks.description IS 'Additional details for the event';
COMMENT ON COLUMN calendar_tasks.is_team_event IS 'Flag to distinguish team events from program-related tasks';