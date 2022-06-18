# youtube-recommender

Recommending YouTube videos based on personal needs, using YouTube API and specified tags / fields of interest through [GenSim](https://radimrehurek.com/gensim/)

Extends on [this](https://github.com/chris-lovejoy/YouTube-video-finder) repo, based on [this](https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a) Medium article

## 1.1 Requirements

- [x] Retrieve videos by search term
- [x] Retrieve captions by video_id
- [x] Dismiss non-English ideos with help of [langid](https://github.com/saffsd/langid.py)
- [x] Join YouTube API metadata and YouTubeTranscriptApi captions data into one dataset
- [x] Create data models
- [x] Save compressed captions data
- [x] Cache search results in PostgreSQL
- [x] Make package installable
- [x] Also cache load captions in `topicer/__main__.py`
- [x] Reconstruct videos tables from cache results
- [ ] Save favourite channels to channels.json, for easy reconstruction of db
- [ ] Containerize the application
- [ ] Run tests in GitHub Actions
- [ ] Create fastAPI api to retrieve this data
- [ ] Create job to collect search results for popular/personal search terms, in order not to exceed API quota (10_000 units/day, [extend quota here](https://support.google.com/youtube/contact/yt_api_form))
- [x] Export personal watch history from YouTube
- [x] Extract personal watch history from YouTube export file, is all metadata accessible?
- [ ] Get all, or popular video **genres**
- [ ] With these genres, try to make **recommendations**
- [ ] Extract plain text/captions from videos, so topic modeling can be applied to it
- [ ] Classify videos by genre, difficulty, (latent) topics, ...
- [ ] Query on categories of videos you watched before: science, AI, ML, python, etc. \
       Collect best videos by custom rating of all these queries. \
       Start recommending videos based on this sample
- [ ] Verify if pushing the same video to postgres only updates changed fields.
- [ ] ...

## 1.2 Nice to haves

- [x] Use async http requests to query YouTube API
- [x] Query captions asynchronously
- [ ] Save Video keywords to db
- [ ] Save Video rating to db

## 2.1 How to install

````bash
# add YouTube v3 API key to youtube_recommender/config/config.yaml first!
# structure:
# api_key:
#   "your_api_key"


# install deps
pip install -r requirements.txt

# download english corpus for SpaCy
python -m spacy download en_core_web_sm

# install app
pip install -U ~/repos/youtube_recommender

# copy configuration files
```bash
cp -r ${SECRETS_DIR}/rarc/config/youtube_recommender/*  ~/anaconda3/envs/py39/lib/python3.9/site-packages/youtube_recommender/config
````

## 2.2 How to run

Search for YouTube videos, example usage:

```bash
# alias ipy="ipython --no-confirm-exit --no-banner -i"

ipy -m youtube_recommender -- 'search term 1' 'search term 2'

# with different search-period (default is 365 days)
# make sure to decrease it for recent videos, or increase it alltime popular videos
ipy -m youtube_recommender -- 'search term 1' --search-period 29

# save top_videos to feather
ipy -m youtube_recommender -- 'search term 1' 'search term 2' --save

# to inspect results, inspect `res` object`, or `df` for only top_videos
```

`python -m youtube_recommender --help`:

```
usage: __main__.py [-h] [--search-period SEARCH_PERIOD] [--dryrun] [-f] [--filter] [-s] [-p] search_terms [search_terms ...]

Defining search parameters

positional arguments:
  search_terms          The terms to query. Can be multiple.

optional arguments:
  -h, --help            show this help message and exit
  --search-period SEARCH_PERIOD
                        The number of days to search for.
  --dryrun              only load modules, do not requests APIs
  -f, --force           force to run query, do not use cache
  --filter              filter non English titles from dataset using langid
  -s, --save            Save results to
  -p, --push_db         push queryResult and Video rows to PostgreSQL`
```

Download captions for YouTube videos, example usage:

```bash
ipy -m youtube_recommender.topicer -- 'video_id_1' 'video_id_2'

# optionally save captions to feather file
ipy -m youtube_recommender.topicer -- 'video_id_1' 'video_id_2' --save_captions

# load video_ids from top_videos.feather file automatically
ipy -m youtube_recommender.topicer -- --save_captions --from_feather

# keep videos data with captions
ipy -m youtube_recommender.topicer -- --save_captions --from_feather --merge_with_videos

# short, most used option:
ipy -m youtube_recommender.topicer -- --from_feather -sp

# to inspect results, inspect `captions` object`
```

`python -m youtube_recommender.topicer --help`:

```
usage: __main__.py [-h] [--from_feather] [-n N] [--dryrun] [-f] [--merge_with_videos] [-s] [-p] [video_ids ...]

Defining parameters

positional arguments:
  video_ids            The YouTube videos to extract captions from. Can be multiple.

optional arguments:
  -h, --help           show this help message and exit
  --from_feather       Import video ids from `/home/paul/repos/youtube-recommender/youtube_recommender/data/top_videos.feather`, created in main.py. ignores any manually passed video_ids
  -n N                 select first `n` rows from feather file
  --dryrun             only load data, do not download captions
  -f, --force          force to download captions, do not use cache
  --merge_with_videos  merge resulting captions dataset with videos metadata
  -s, --save_captions  Save captions to `/home/paul/repos/youtube-recommender/youtube_recommender/data/captions.feather`
  -p, --push_db        push Video, Channel and Caption rows to PostgreSQL`
```
