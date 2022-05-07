from typing import Any, Dict, NewType, Type, Union

VideoId = NewType("VideoId", str)
ChannelId = NewType("ChannelId", str)
CaptionId = NewType("CaptionId", str)

TableTypes = Union[Type["Video"], Type["Channel"], Type["queryResult"]]

Record = NewType("Record", Dict[str, Any])

VideoRec = NewType("VideoRec", Record)
ChannelRec = NewType("ChannelRec", Record)
CaptionRec = NewType("CaptionRec", Record)
