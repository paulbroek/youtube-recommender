DROP MATERIALIZED VIEW vw_last_videos;
DROP MATERIALIZED VIEW last_videos;

CREATE MATERIALIZED VIEW last_videos AS
SELECT
    video.id AS video_id,
    video.channel_id,
    video.views,
    video.custom_score,
    channel.name AS channel_name,
    channel.num_subscribers,
    query_result.query,
    query_result.id AS qr_id,
    query_result.updated AS qr_updated,
    video.title,
    video.description,
    -- video.created,
    date_trunc('seconds', video.updated) AS updated
FROM
    query_video_association qva
    INNER JOIN video ON qva.video_id = video.id
    INNER JOIN channel ON channel.id = video.channel_id
    LEFT JOIN query_result ON qva.query_result_id = query_result.id
ORDER BY
    video.updated DESC
LIMIT
    10000 WITH DATA;

CREATE MATERIALIZED VIEW vw_last_videos AS
SELECT
    lv.video_id,
    lv.channel_id,
    lv.channel_name,
    lv.num_subscribers,
    lv.qr_id,
    lv.query,
    lv.qr_updated,
    concat(left(lv.title, 60), '...') AS trunc_title,
    concat(left(lv.description, 60), '...') AS trunc_description,
    NOW() - lv.updated AS updated_ago
FROM
    last_videos lv WITH DATA;

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
