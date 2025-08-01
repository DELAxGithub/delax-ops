/*
  # Add PR management fields

  1. Changes
    - Add `pr_completed` boolean field to programs table
    - Add `pr_due_date` date field to programs table
    - Set default values for existing records

  2. Data Migration
    - Set pr_completed=true for program_id 001-009
    - Set pr_completed=false for program_id 010 and above
*/

-- Add new columns
ALTER TABLE programs 
  ADD COLUMN IF NOT EXISTS pr_completed boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS pr_due_date date;

-- Update existing records
UPDATE programs
SET pr_completed = CASE
  WHEN SUBSTRING(program_id FROM '\d+')::integer < 10 THEN true
  ELSE false
END;