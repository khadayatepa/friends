-- ============================================================
-- 01_create_user.sql
-- RUN THIS CONNECTED AS  ADMIN  TO YOUR AUTONOMOUS DATABASE.
--   How: OCI Console -> your ADB -> Database Actions -> SQL
--        (or SQLcl / SQL Developer connected as ADMIN).
--
-- Creates a dedicated, low-privilege schema for the Friends app.
-- The Streamlit app will connect as this user (NOT as ADMIN),
-- using your service alias  prashant26ai_medium.
-- ============================================================

-- 1) Create the application user / schema.
--    ADB password rules: at least 12 chars, with at least one UPPERCASE,
--    one lowercase and one digit, and it must NOT contain the username.
--    >>> CHANGE THE PASSWORD BELOW before running, and keep it safe -
--        you will paste it into Streamlit secrets later. <<<
CREATE USER friends_app IDENTIFIED BY "Fr1ends#Map2026!"
  DEFAULT TABLESPACE DATA
  TEMPORARY TABLESPACE TEMP
  QUOTA UNLIMITED ON DATA;

-- 2) Grant only what the app needs.
GRANT CREATE SESSION  TO friends_app;
GRANT CREATE TABLE    TO friends_app;
GRANT CREATE SEQUENCE TO friends_app;   -- used by IDENTITY columns
GRANT CREATE VIEW     TO friends_app;

-- 3) (OPTIONAL) Let this schema sign in to the Database Actions web UI,
--    so you can browse its tables in a browser. Uncomment to enable.
-- BEGIN
--   ORDS_ADMIN.ENABLE_SCHEMA(p_schema => 'FRIENDS_APP');
-- END;
-- /

-- Done. Next: connect AS friends_app and run 02_schema.sql.
-- Verify with:
--   SELECT username, account_status FROM dba_users WHERE username = 'FRIENDS_APP';
