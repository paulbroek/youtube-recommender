DROP MATERIALIZED VIEW last_videos;
CREATE MATERIALIZED VIEW last_videos AS
SELECT
    video.id AS video_id,
    video.channel_id,
    query_result.query,
    concat(left(video.title, 60), '...') AS trunc_title,
    concat(left(video.description, 60), '...') AS trunc_description,
    -- video.created,
    date_trunc('seconds', video.updated) AS updated,
    NOW() - video.updated AS updated_ago
FROM
    query_video_association qva
    LEFT JOIN video ON qva.video_id = video.id
    LEFT JOIN query_result ON qva.query_result_id = query_result.id
ORDER BY
    video.updated DESC
LIMIT
    10000 WITH DATA;

DROP MATERIALIZED VIEW last_query_results;
CREATE MATERIALIZED VIEW last_query_results AS
SELECT
    qr.id AS query_id,
    qr.query,
    COUNT(video.id) AS nvid,
    date_trunc('seconds', qr.updated) AS updated,
    NOW() - qr.updated AS updated_ago
FROM
    query_video_association qva
    LEFT JOIN video ON qva.video_id = video.id
    LEFT JOIN query_result AS qr ON qva.query_result_id = qr.id
GROUP BY
    qr.id
ORDER BY
    qr.updated DESC
LIMIT
    100 WITH DATA;