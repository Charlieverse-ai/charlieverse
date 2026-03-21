-- Add date range columns to work_logs for processed event tracking
ALTER TABLE work_logs ADD COLUMN start_date TEXT;
ALTER TABLE work_logs ADD COLUMN end_date TEXT;
