SELECT
    video_id,
    CASE
        WHEN LENGTH (title) > 70 THEN concat(trim(left(title, 70)), '...')
        ELSE title
    END AS trunc_title,
    CASE
        WHEN LENGTH (description) > 120 THEN concat(trim(left(description, 120)), '...')
        ELSE description
    END AS trunc_description
FROM
    last_videos
LIMIT
    3;
-- select most frequent used keywords
select
    keyword_id,
    keyword.name,
    count(keyword_id)
from
    video_keyword_association vka
    INNER JOIN keyword ON vka.keyword_id = keyword.id
group by
    keyword_id,
    keyword.name
ORDER BY
    count DESC
limit
    25;
-- select top channels
DROP VIEW top_channels;
CREATE VIEW top_channels AS
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
    5;
