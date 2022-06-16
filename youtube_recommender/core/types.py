"""types.py, define types for youtube-recommender."""

from typing import Any, Dict, NewType, Union  # , Type

VideoId = NewType("VideoId", str)
ChannelId = NewType("ChannelId", str)
CaptionId = NewType("CaptionId", str)

Video = NewType("Video", dict)
Channel = NewType("Channel", dict)
queryResult = NewType("queryResult", dict)

# TableTypes = Union[Type["Video"], Type["Channel"], Type["queryResult"]]
TableTypes = Union[Video, Channel, queryResult]

Record = NewType("Record", Dict[str, Any])

VideoRec = NewType("VideoRec", Record)
ChannelRec = NewType("ChannelRec", Record)
CaptionRec = NewType("CaptionRec", Record)
