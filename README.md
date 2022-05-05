# youtube-recommender

Recommending YouTube videos based on personal needs, using YouTube API and specified tags / fields of interest through [GenSim](https://radimrehurek.com/gensim/)

Extends on [this](https://github.com/chris-lovejoy/YouTube-video-finder) repo, based on [this](https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a) Medium article

## 1.1 Requirements

-   [x] Retrieve videos by search term
-   [x] Retrieve captions by video_id
-   [x] Dismiss non-English ideos with help of [langid](https://github.com/saffsd/langid.py)
-   [x] Join YouTube API metadata and YouTubeTranscriptApi captions data into one dataset
-   [ ] Create data models in order to cache results to PostgreSQL
-   [ ] Create fastAPI api to retrieve this data
-   [ ] Create job to collect search results for popular/personal search terms, in order not to exceed API quota (10_000 units/day, (extend quota here)[https://support.google.com/youtube/contact/yt_api_form])
-   [ ] Retrieve personal watch history
-   [ ] Get all, or popular video **genres**
-   [ ] With these genres, try to make **recommendations**
-   [ ] Extract plain text/captions from videos, so topic modeling can be applied to it
-   [ ] Classify videos by genre, difficulty, (latent) topics, ...
-   [ ] Query on categories of videos you watched before: science, AI, ML, python, etc. \
         Collect best videos by custom rating of all these queries. \
         Start recommending videos based on this sample
-   [ ] ...

## 1.2 Nice to haves

-   [x] Use async http requests to query YouTube API
-   [x] Query captions asynchronously

## 2.1 How to install

```bash
# add YouTube v3 API key to config.yaml first!

# install deps
pip install -r requirements.txt

# download english corpus for SpaCy
python -m spacy download en_core_web_sm
```

## 2.2 How to run

Search for YouTube videos, example usage:

```bash
# alias ipy="ipython --no-confirm-exit --no-banner -i"

ipy youtube-recommender/main.py -- 'search term 1' 'search term 2'

# with different search-period (default is 7 days)
ipy youtube-recommender/main.py -- 'search term 1' --search-period 29

# save top_videos to feather
ipy youtube-recommender/main.py -- 'search term 1' 'search term 2' --save

# to inspect results, inspect `res` object`, or `df` for only top_videos
```

`main.py` help:

```
usage: main.py [-h] [--search-period SEARCH_PERIOD] [--filter] [-s] search_terms [search_terms ...]

Defining search parameters

positional arguments:
  search_terms          The terms to query. Can be multiple.

optional arguments:
  -h, --help            show this help message and exit
  --search-period SEARCH_PERIOD
                        The number of days to search for.
  --filter              filter non English titles from dataset using langid
  -s, --save            Save results to
```

Download captions for YouTube videos, example usage:

```bash
ipy youtube-recommender/topicer.py -- 'video_id_1' 'video_id_2'

# optionally save captions to feather file
ipy youtube-recommender/topicer.py -- 'video_id_1' 'video_id_2' --save_captions

# load video_ids from top_videos.feather file automatically
ipy youtube-recommender/topicer.py -- --save_captions --from_feather

# keep videos data with captions
ipy youtube-recommender/topicer.py -- --save_captions --from_feather --merge_with_videos

# to inspect results, inspect `captions` object`
```

`topicer.py` help:

```
usage: topicer.py [-h] [--from_feather] [-n N] [--dryrun] [--merge_with_videos] [-s] [video_ids ...]

Defining parameters

positional arguments:
  video_ids            The YouTube videos to extract captions from. Can be multiple.

optional arguments:
  -h, --help           show this help message and exit
  --from_feather       Import video ids from `youtube-recommender/data/top_videos.feather`, created in main.py. ignores any manually passed video_ids
  -n N                 select first `n` rows from feather file
  --dryrun             only load data, do not download captions
  --merge_with_videos  merge resulting captions dataset with videos metadata
  -s, --save_captions  Save captions to `youtube-recommender/data/captions.feather`
```
