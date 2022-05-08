-- trigger functions

CREATE OR REPLACE FUNCTION refresh_last_query_results()
RETURNS TRIGGER LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW last_query_results;
    RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION refresh_last_videos()
RETURNS TRIGGER LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW last_videos;
    RETURN NULL;
END $$;

-- triggers

-- todo: why is running AFTER last record was inserted? it lags behind by 1 
DROP TRIGGER IF EXISTS refresh_last_query_results ON query_result;
CREATE TRIGGER refresh_last_query_results
BEFORE INSERT OR UPDATE OR DELETE
ON query_result
FOR EACH ROW
-- FOR EACH STATEMENT
EXECUTE PROCEDURE refresh_last_query_results();

DROP TRIGGER IF EXISTS refresh_last_videos ON query_result;
CREATE TRIGGER refresh_last_videos
AFTER INSERT OR UPDATE OR DELETE
ON query_result
FOR EACH ROW
EXECUTE PROCEDURE refresh_last_videos();
