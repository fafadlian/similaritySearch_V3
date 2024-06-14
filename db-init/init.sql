DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'muhammadfathifadlian') THEN
      CREATE USER muhammadfathifadlian WITH ENCRYPTED PASSWORD 'changememf2022';
   END IF;
END
$$;

DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'similaritysearch') THEN
      CREATE DATABASE similaritysearch WITH OWNER muhammadfathifadlian;
   END IF;
END
$$;
\connect similaritysearch;

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR PRIMARY KEY,
    folder_path VARCHAR,
    status VARCHAR,
    flight_ids TEXT,
    flight_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
