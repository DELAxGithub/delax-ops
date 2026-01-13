/*
  # Create programs table

  1. New Tables
    - `programs`
      - `id` (bigint, primary key, auto-increment)
      - `program_id` (text)
      - `title` (text, required)
      - `subtitle` (text)
      - `status` (text, required)
      - `first_air_date` (date)
      - `re_air_date` (date)
      - `filming_date` (date)
      - `complete_date` (date)
      - `cast1` (text)
      - `cast2` (text)
      - `script_url` (text)
      - `pr_text` (text)
      - `notes` (text)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `programs` table
    - Add policies for authenticated users to:
      - Read all programs
      - Create new programs
      - Update any program
      - Delete any program

  3. Triggers
    - Add trigger to update `updated_at` timestamp
*/

-- Create the programs table
CREATE TABLE IF NOT EXISTS programs (
  id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  program_id text,
  title text NOT NULL,
  subtitle text,
  status text NOT NULL,
  first_air_date date,
  re_air_date date,
  filming_date date,
  complete_date date,
  cast1 text,
  cast2 text,
  script_url text,
  pr_text text,
  notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE programs ENABLE ROW LEVEL SECURITY;

-- Create policies if they don't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'programs' 
    AND policyname = 'Enable read access for authenticated users'
  ) THEN
    CREATE POLICY "Enable read access for authenticated users"
      ON programs
      FOR SELECT
      TO authenticated
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'programs' 
    AND policyname = 'Enable insert access for authenticated users'
  ) THEN
    CREATE POLICY "Enable insert access for authenticated users"
      ON programs
      FOR INSERT
      TO authenticated
      WITH CHECK (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'programs' 
    AND policyname = 'Enable update access for authenticated users'
  ) THEN
    CREATE POLICY "Enable update access for authenticated users"
      ON programs
      FOR UPDATE
      TO authenticated
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies 
    WHERE tablename = 'programs' 
    AND policyname = 'Enable delete access for authenticated users'
  ) THEN
    CREATE POLICY "Enable delete access for authenticated users"
      ON programs
      FOR DELETE
      TO authenticated
      USING (true);
  END IF;
END
$$;

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ language 'plpgsql';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger 
    WHERE tgname = 'update_programs_updated_at'
  ) THEN
    CREATE TRIGGER update_programs_updated_at
      BEFORE UPDATE ON programs
      FOR EACH ROW
      EXECUTE FUNCTION update_updated_at_column();
  END IF;
END
$$;