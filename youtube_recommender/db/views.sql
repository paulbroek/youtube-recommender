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

-- moving away from queryResult version of youtube-recommender
-- CREATE MATERIALIZED VIEW vw_last_videos AS
-- SELECT
    -- lv.video_id,
    -- lv.channel_id,
    -- lv.channel_name,
    -- lv.num_subscribers,
    -- lv.qr_id,
    -- lv.query,
    -- lv.qr_updated,
    -- CASE
        -- WHEN LENGTH (title) > 60 THEN concat(trim(left(title, 60)), '...')
        -- ELSE title
    -- END AS trunc_title,
    -- CASE
        -- WHEN LENGTH (lv.description) > 60 THEN concat(trim(left(lv.description, 60)), '...')
        -- ELSE lv.description
    -- END AS trunc_description,
    -- NOW() - lv.updated AS updated_ago
-- FROM
    -- last_videos lv WITH DATA;

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


-- view videos with nchapter
DROP MATERIALIZED VIEW vw_videos_with_chapters;
CREATE MATERIALIZED VIEW vw_videos_with_chapters AS
SELECT
    video.id AS video_id,
    COUNT(chapter.video_id) AS nchapter
FROM
    chapter
    INNER JOIN video ON video.id = chapter.video_id
GROUP BY
    video.id
ORDER BY
    nchapter DESC
LIMIT 
    10000 WITH DATA;


-- view comments with truncated text
DROP MATERIALIZED VIEW vw_comments;
CREATE MATERIALIZED VIEW vw_comments AS
SELECT
    left(comment.id, 14) AS trunc_id,
    CASE
        WHEN LENGTH (text) > 100 THEN concat(trim(left(text, 100)), '...')
        ELSE text
    END AS trunc_text,
    LENGTH(text) as length,
    comment.votes AS votes,
    channel.name AS user_name,
    CASE
        WHEN LENGTH (video.title) > 50 THEN concat(trim(left(video.title, 50)), '...')
        ELSE video.title
    END AS trunc_video_title
FROM
    comment
    INNER JOIN video ON video.id = comment.video_id
    INNER JOIN channel ON channel.id = comment.channel_id
ORDER BY
    votes DESC
LIMIT 
    100000 WITH DATA;


-- view users with most votes
DROP MATERIALIZED VIEW vw_users_with_most_votes;
CREATE MATERIALIZED VIEW vw_users_with_most_votes AS
SELECT
    channel.name AS user_name,
    -- LENGTH(text) as length,
    COUNT(comment.id) AS ncomment,
    SUM(comment.votes) AS total_votes
FROM
    comment
    INNER JOIN video ON video.id = comment.video_id
    INNER JOIN channel ON channel.id = comment.channel_id
GROUP BY
    channel.id
ORDER BY
    total_votes DESC
LIMIT 
    100000 WITH DATA;

-- view top views, can be used for videos that didn't scrape comments yet
DROP MATERIALIZED VIEW top_videos;
CREATE MATERIALIZED VIEW top_videos AS
SELECT
    video.id AS video_id,
    channel.id AS channel_id,
    channel.name AS channel_name,
    video.title,
    video.views,
    video.length,
    video.nchapter
FROM
    (
        SELECT video.*, COUNT(chapter.video_id) AS nchapter from chapter INNER JOIN video ON video.id = chapter.video_id GROUP BY video.id
    ) video
        INNER JOIN channel ON video.channel_id = channel.id
GROUP BY
    video.id,
    video.title,
    video.views,
    video.length,
    channel.id,
    video.nchapter
ORDER BY
    views DESC
LIMIT 
    90000 WITH DATA;

-- todo: rewrite without having to groupby so many ids
-- view videos with most comments
DROP MATERIALIZED VIEW top_videos_with_comments;
CREATE MATERIALIZED VIEW top_videos_with_comments AS
SELECT
    video.id AS video_id,
    channel.id AS channel_id,
    channel.name AS channel_name,
    CASE
        WHEN LENGTH (video.title) > 60 THEN concat(trim(left(video.title, 60)), '...')
        ELSE video.title
    END AS trunc_video_title,
    COUNT(comment.id) AS ncomment,
    LPAD(TO_CHAR(COUNT(comment.id), 'fm999G999G999'), 12) AS ncomment_fmt,
    LPAD(TO_CHAR(video.views, 'fm999G999G999'), 12) AS views,
    TO_CHAR((video.length || ' second')::interval, 'HH24:MI:SS') AS duration,
    video.nchapter
FROM
    (
        SELECT video.*, COUNT(chapter.video_id) AS nchapter from chapter INNER JOIN video ON video.id = chapter.video_id GROUP BY video.id
    ) video
        INNER JOIN channel ON video.channel_id = channel.id
        INNER JOIN comment ON video.id = comment.video_id
GROUP BY
    video.id,
    video.title,
    video.views,
    video.length,
    channel.id,
    video.nchapter
ORDER BY
    ncomment DESC
LIMIT 
    90000 WITH DATA;

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
    100;

-- to also see channels without comments: they need comment scraping
DROP MATERIALIZED VIEW top_channels_with_comments;
CREATE MATERIALIZED VIEW top_channels_with_comments AS
SELECT DISTINCT
    channel.name AS channel_name,
    channel.id AS channel_id,
    COUNT(DISTINCT video.id) AS video_count,
    SUM(video.views) AS total_views,
    COUNT(comment.id) AS comment_count
    -- summing here creates duplicate sums
    -- SUM(video.views) AS total_views,
    -- LPAD(TO_CHAR(SUM(video.views), 'fm999G999G999G999'), 15) AS total_views_fmt
FROM
    video
    INNER JOIN channel ON video.channel_id = channel.id
    LEFT JOIN comment ON video.id = comment.video_id
GROUP BY
    GROUPING SETS (
        (channel.id, channel.name),
        (comment.id)
    )
ORDER BY
    video_count DESC
LIMIT
    200;

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
