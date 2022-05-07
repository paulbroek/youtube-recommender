-- trigger functions

CREATE OR REPLACE FUNCTION refresh_last_videos()
RETURNS TRIGGER LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW last_videos;
    RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION refresh_last_query_results()
RETURNS TRIGGER LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW last_query_results;
    RETURN NULL;
END $$;

-- triggers

CREATE TRIGGER refresh_last_videos_by_query
AFTER INSERT OR UPDATE OR DELETE
ON query_result
FOR EACH ROW
EXECUTE PROCEDURE refresh_last_videos();

-- drop this trigger by executing: 
-- DROP TRIGGER refresh_last_videos_by_query ON query_result;

CREATE TRIGGER refresh_last_query_results
AFTER INSERT OR UPDATE OR DELETE
ON query_result
FOR EACH ROW
EXECUTE PROCEDURE refresh_last_query_results();

-- drop this trigger by executing: 
-- DROP TRIGGER refresh_last_query_results ON query_result;
