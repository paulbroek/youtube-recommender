# youtube-recommender

Recommending YouTube videos based on personal needs, using YouTube API and specified tags / fields of interest through [GenSim](https://radimrehurek.com/gensim/)

Extends on [this](https://github.com/chris-lovejoy/YouTube-video-finder) repo, based on [this](https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a) Medium article

## 1.1 Requirements

-   [x] Retrieve videos by search term
-   [x] Retrieve captions by video_id
-   [ ] Dismiss non-English ideos by using [fastText](https://github.com/facebookresearch/fastText)
-   [ ] Join YouTube API metadata and YouTubeTranscriptApi captions data into one dataset
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

-   [ ] Use async http requests to query YouTube API

## 2.1 How to install

```bash
# add YouTube v3 API key to config.yaml first!

# install deps
pip install -r requirements.txt

# download english corpus for SpaCy
python -m spacy download en
```

## 2.2 How to run

Search for YouTube videos

```bash
# alias ipy="ipython --no-confirm-exit --no-banner -i"

ipy youtube-recommender/main.py 'search term 1' 'search term 2'

# with different search-period (default is 7 days)
ipy youtube-recommender/main.py 'search term 1' --search-period 29

# to inspect results, inspect `res` object`
```

Download captions for YouTube videos, optionally extract latent topics

```bash
ipy youtube-recommender/topicer.py -- 'video_id_1' 'video_id_2'

# optionally save captions to feather file
ipy youtube-recommender/topicer.py -- 'video_id_1' 'video_id_2' --save_captions

# to inspect results, inspect `captions` object`
```
