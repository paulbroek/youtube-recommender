
  
"""
    connect.py
    connect to YouTube API and list videos by popularity
    based on:
        https://towardsdatascience.com/i-created-my-own-youtube-algorithm-to-stop-me-wasting-time-afd170f4ca3a
    API help:
        https://developers.google.com/youtube/v3/quickstart/python
"""

from googleapiclient.discovery import build

# Call the YouTube API. To create API Key, go to Gogole cloud console -> Enable APIs page, and find "YouTube Data API v3"
# api_key =  # Enter your own API key – this one won’t work

youtube_api = build("youtube", "v3", developerKey=api_key)

search_terms = ['business'] 

results = youtube_api.search().list(q=search_terms, part="snippet", type="video",
                                    order="viewCount", maxResults=50).execute()

request = youtube_api.channels().list()
response = request.execute()

print(response)