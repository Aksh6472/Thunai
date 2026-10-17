-- Runs once, on first initialisation of the Postgres volume.
-- Creates the separate test database (TESTING.md §3). The main DB comes from POSTGRES_DB.
CREATE DATABASE thunai_test OWNER thunai;
