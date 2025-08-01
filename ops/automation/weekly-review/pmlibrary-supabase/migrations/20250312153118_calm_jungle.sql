/*
  # Add calendar tasks functionality

  1. New Tables
    - `calendar_tasks`
      - `id` (uuid, primary key)
      - `program_id` (bigint, foreign key to programs.id, optional)
      - `task_type` (text, required)
      - `start_date` (date, required)
      - `end_date` (date, required)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `calendar_tasks` table
    - Add policies for authenticated users to perform CRUD operations

  3. Foreign Keys
    - Add foreign key constraint to programs table
*/

-- Create calendar_tasks table
CREATE TABLE calendar_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  program_id bigint REFERENCES programs(id) ON DELETE SET NULL,
  task_type text NOT NULL,
  start_date date NOT NULL,
  end_date date NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  -- Ensure end_date is not before start_date
  CONSTRAINT valid_date_range CHECK (end_date >= start_date)
);

-- Enable RLS
ALTER TABLE calendar_tasks ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Enable read access for authenticated users"
  ON calendar_tasks
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Enable insert access for authenticated users"
  ON calendar_tasks
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users"
  ON calendar_tasks
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable delete access for authenticated users"
  ON calendar_tasks
  FOR DELETE
  TO authenticated
  USING (true);

-- Create updated_at trigger
CREATE TRIGGER update_calendar_tasks_updated_at
  BEFORE UPDATE ON calendar_tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Create index for better query performance
CREATE INDEX idx_calendar_tasks_dates ON calendar_tasks (start_date, end_date);
CREATE INDEX idx_calendar_tasks_program_id ON calendar_tasks (program_id);