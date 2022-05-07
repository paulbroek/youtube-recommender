from typing import NewType, Type, Union

VideoId = NewType("VideoId", str)
ChannelId = NewType("ChannelId", str)
CaptionId = NewType("CaptionId", str)

TableTypes = Union[Type["Video"], Type["Channel"], Type["queryResult"]]
