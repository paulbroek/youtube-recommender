# youtube-recommender

Recommending YouTube videos based on personal needs, using YouTube API and specified tags / fields of interest through [GenSim](https://radimrehurek.com/gensim/) and [BERTopic](https://github.com/MaartenGr/BERTopic)

Extends on [this](https://github.com/chris-lovejoy/YouTube-video-finder) project, based on [this](https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a) Medium article

[pytube](https://github.com/pytube/pytube) is used to scrape video metadata
[youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) is used to download captions

## 1.0 Config

```bash
# add YouTube v3 API key to youtube_recommender/config/config.yaml
# structure:
# api_key:
#   "your_api_key"

# copy configuration files
# to installed package
cp -r ${SECRETS_DIR}/rarc/config/youtube_recommender/*  ~/anaconda3/envs/py39/lib/python3.9/site-packages/youtube_recommender/config
# to cloned repo
cp -r ${SECRETS_DIR}/rarc/config/youtube_recommender/*  ~/repos/youtube-recommender/youtube_recommender/config
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

## 2.2.1 How to run the package

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
usage: __main__.py [-h] [--search-period SEARCH_PERIOD] [--dryrun] [-f] [--filter] [-n NITEMS] [-s] [-p] search_terms [search_terms ...]

Defining search parameters

positional arguments:
  search_terms          The terms to query. Can be multiple.

options:
  -h, --help            show this help message and exit
  --search-period SEARCH_PERIOD
                        The number of days to search for.
  --dryrun              only load modules, do not requests APIs
  -f, --force           force to run query, do not use cache
  --filter              filter non English titles from dataset using langid
  -n NITEMS, --nitems NITEMS
                        Max search results to fetch from YouTube API
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

# download video caption and save to clipboard
python -m youtube_recommender.topicer --with_start_times --to_clipboard \
  VIDEO_ID
```

`python -m youtube_recommender.topicer --help`:

```
usage: __main__.py [-h] [--from_feather] [-n N] [--dryrun] [-f] [--merge_with_videos] [--with_start_times] [-s] [-c] [-p] [video_ids ...]

Defining parameters

positional arguments:
  video_ids            The YouTube videos to extract captions from. Can be multiple.

options:
  -h, --help           show this help message and exit
  --from_feather       Import video ids from `/home/paul/repos/youtube-recommender/youtube_recommender/data/top_videos.feather`, created in main.py. ignores any manually passed video_ids
  -n N                 select first `n` rows from feather file
  --dryrun             only load data, do not download captions
  -f, --force          force to download captions, do not use cache
  --merge_with_videos  merge resulting captions dataset with videos metadata
  --with_start_times   include start_times in the output caption string
  -s, --save_captions  Save captions to `/home/paul/repos/youtube-recommender/youtube_recommender/data/captions.feather`
  -c, --to_clipboard   Save captions to clipboard
  -p, --push_db        push Video, Channel and Caption rows to PostgreSQL`
```

## 2.2.2 Run notebook files in IPython

Convert `.ipynb` to `.py` files and run them in `ipython`

```bash
cd ~/repos/youtube-recommender/youtube_recommender
jupyter nbconvert --to script recommend/logistic_regression/train.ipynb && ipy recommend/logistic_regression/train.py
```

## 2.2.3 Build and run distributed scraper

Deploy locally with `docker-compose`

```bash
# rsync nginx configuration: nginx.cert and nginx.key
rsync -avz -e "ssh -p PORT" --progress USER@HOST:/home/paul/repos/youtube-recommender/cert ~/repos/youtube-recommender
# create network
docker network create microservices
# deploy scraper
docker-compose up --build --scale scrape-service=5 && docker-compose logs -f
# check if reverseproxy is running succesfully
docker logs youtube-recommender_nginx-reverseproxy_1 --tail 20 -f
# maybe convert service names manually to upstream nginx servers
cd ./nginx
chmod +x ./save_server_names.sh
./save_server_names.sh ./includes/grpcservers
```

Deploy to production with Kubernetes:

```bash
# only deploy scrape-service and its secret files
k apply -f $(find ./kubernetes -name 'scrape-service*.yaml' -o -name '*secret.yaml' -type f | tr '\n' ',' | sed 's/,$//')
```
