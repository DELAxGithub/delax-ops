/*
  # Create programs table

  1. New Tables
    - `programs`
      - `id` (bigint, primary key)
      - `program_id` (text)
      - `first_air_date` (date)
      - `filming_date` (date)
      - `complete_date` (date)
      - `title` (text)
      - `subtitle` (text)
      - `status` (text)
      - `cast1` (text)
      - `cast2` (text)
      - `notes` (text)
      - `script_url` (text)
      - `pr_80text` (text)
      - `pr_200text` (text)
      - `re_air_date` (date)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `programs` table
    - Add policies for authenticated users to perform CRUD operations
    - Add trigger for updating updated_at timestamp
*/

-- Create programs table if it doesn't exist
DO $$ BEGIN
  CREATE TABLE IF NOT EXISTS programs (
    id bigint PRIMARY KEY,
    program_id text,
    first_air_date date,
    filming_date date,
    complete_date date,
    title text,
    subtitle text,
    status text,
    cast1 text,
    cast2 text,
    notes text,
    script_url text,
    pr_80text text,
    pr_200text text,
    re_air_date date,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
  );
EXCEPTION
  WHEN duplicate_table THEN
    NULL;
END $$;

-- Enable Row Level Security if not already enabled
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DO $$ BEGIN
  DROP POLICY IF EXISTS "Enable read access for authenticated users" ON programs;
  DROP POLICY IF EXISTS "Enable insert access for authenticated users" ON programs;
  DROP POLICY IF EXISTS "Enable update access for authenticated users" ON programs;
  DROP POLICY IF EXISTS "Enable delete access for authenticated users" ON programs;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

-- Create policies for authenticated users
CREATE POLICY "Enable read access for authenticated users"
  ON programs
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Enable insert access for authenticated users"
  ON programs
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users"
  ON programs
  FOR UPDATE
  TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Enable delete access for authenticated users"
  ON programs
  FOR DELETE
  TO authenticated
  USING (true);

-- Create or replace updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing trigger if it exists and create new one
DO $$ BEGIN
  DROP TRIGGER IF EXISTS update_programs_updated_at ON programs;
EXCEPTION
  WHEN undefined_object THEN
    NULL;
END $$;

CREATE TRIGGER update_programs_updated_at
  BEFORE UPDATE ON programs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();