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

DROP TRIGGER IF EXISTS refresh_last_videos_by_query ON video;
CREATE TRIGGER refresh_last_videos_by_query
AFTER INSERT OR UPDATE OR DELETE
ON video
-- ON query_result
FOR EACH ROW
EXECUTE PROCEDURE refresh_last_videos();

DROP TRIGGER IF EXISTS refresh_last_query_results ON video;
CREATE TRIGGER refresh_last_query_results
AFTER INSERT OR UPDATE OR DELETE
ON video
-- ON query_result
FOR EACH ROW
EXECUTE PROCEDURE refresh_last_query_results();
