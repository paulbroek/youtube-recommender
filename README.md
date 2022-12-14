# youtube-recommender

Recommending YouTube videos based on personal needs, using YouTube API and specified tags / fields of interest through [GenSim](https://radimrehurek.com/gensim/)

Extends on [this](https://github.com/chris-lovejoy/YouTube-video-finder) repo, based on [this](https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a) Medium article

## 1.0 Config

```bash
# add YouTube v3 API key to youtube_recommender/config/config.yaml
# structure:
# api_key:
#   "your_api_key"

# copy configuration files
cp -r ${SECRETS_DIR}/rarc/config/youtube_recommender/*  ~/anaconda3/envs/py39/lib/python3.9/site-packages/youtube_recommender/config
```

## 2.1 How to install

```bash
# install deps
pip install -r requirements.txt

# download english corpus for SpaCy
python -m spacy download en_core_web_sm

# install app
pip install -U ~/repos/youtube_recommender
```

## 2.2.1 How to run

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

## 2.2.2 Run notebook files in IPython

Convert `.ipynb` to `.py` files and run them in `ipython`

```bash
cd ~/repos/youtube-recommender/youtube_recommender
jupyter nbconvert --to script recommend/logistic_regression/train.ipynb && ipy recommend/logistic_regression/train.py
```
