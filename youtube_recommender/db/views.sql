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
    video.is_educational,
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
    20000 WITH DATA;

CREATE MATERIALIZED VIEW vw_last_videos AS
SELECT
    lv.video_id,
    lv.channel_id,
    lv.channel_name,
    lv.num_subscribers,
    lv.qr_id,
    lv.query,
    lv.qr_updated,
    CASE
        WHEN LENGTH (title) > 60 THEN concat(trim(left(title, 60)), '...')
        ELSE title
    END AS trunc_title,
    CASE
        WHEN LENGTH (lv.description) > 60 THEN concat(trim(left(lv.description, 60)), '...')
        ELSE lv.description
    END AS trunc_description,
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

-- view videos with most comments
DROP MATERIALIZED VIEW top_videos_with_comments;
CREATE MATERIALIZED VIEW top_videos_with_comments AS
SELECT
    video.id AS video_id,
    CASE
        WHEN LENGTH (video.title) > 60 THEN concat(trim(left(video.title, 60)), '...')
        ELSE video.title
    END AS trunc_video_title,
    count(comment.id) as ncomment,
    channel.id AS channel_id,
    channel.name AS channel_name
FROM
    video
    INNER JOIN channel ON video.channel_id = channel.id
    INNER JOIN comment ON video.id = comment.video_id
GROUP BY
    video.id,
    channel.id
ORDER BY
    ncomment DESC
LIMIT 
    500 WITH DATA;

-- view top channels
DROP MATERIALIZED VIEW top_channels;
CREATE MATERIALIZED VIEW top_channels AS
SELECT
    channel.name,
    channel.id,
    COUNT(video) AS video_count
FROM
    video
    INNER JOIN channel ON video.channel_id = channel.id
GROUP BY
    channel.id
ORDER BY
    video_count DESC
LIMIT
    15;

-- view top keywords
DROP MATERIALIZED VIEW top_keywords;
CREATE MATERIALIZED VIEW top_keywords AS
SELECT
    keyword.name AS keyword_name,
    COUNT(vka.video_id) AS keyword_count
FROM
    video_keyword_association vka
    LEFT JOIN keyword ON keyword.id = vka.keyword_id
    -- INNER JOIN video ON video.id = vka.video_id
    -- INNER JOIN channel ON channel.id = video.channel_id
GROUP BY 
    keyword.id
ORDER BY
    keyword_count DESC
LIMIT
    10000 WITH DATA;

-- view channels by educational
-- can use COALESCE(video.is_educational, 'f')
-- but now it's more clear that videos have not been classified yet. 
DROP MATERIALIZED VIEW channels_over_educational;
CREATE MATERIALIZED VIEW channels_over_educational AS
SELECT channel.id, channel.name, count(*) as nvideo,
       avg( video.is_educational::int ) as pct_educational
FROM channel
    INNER JOIN video ON video.channel_id = channel.id
GROUP BY channel.id
LIMIT 50;

-- view channels by categories
