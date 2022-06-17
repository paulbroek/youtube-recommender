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
