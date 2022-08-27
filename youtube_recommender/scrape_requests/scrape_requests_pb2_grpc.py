# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import scrape_requests_pb2 as scrape__requests__pb2


class ChannelScrapingsStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Scrape = channel.unary_unary(
                '/ChannelScrapings/Scrape',
                request_serializer=scrape__requests__pb2.ScrapeRequest.SerializeToString,
                response_deserializer=scrape__requests__pb2.ChannelScrapeResponse.FromString,
                )


class ChannelScrapingsServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Scrape(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ChannelScrapingsServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Scrape': grpc.unary_unary_rpc_method_handler(
                    servicer.Scrape,
                    request_deserializer=scrape__requests__pb2.ScrapeRequest.FromString,
                    response_serializer=scrape__requests__pb2.ChannelScrapeResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'ChannelScrapings', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class ChannelScrapings(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Scrape(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/ChannelScrapings/Scrape',
            scrape__requests__pb2.ScrapeRequest.SerializeToString,
            scrape__requests__pb2.ChannelScrapeResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)


class VideoScrapingsStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Scrape = channel.unary_unary(
                '/VideoScrapings/Scrape',
                request_serializer=scrape__requests__pb2.ScrapeRequest.SerializeToString,
                response_deserializer=scrape__requests__pb2.VideoScrapeResponse.FromString,
                )


class VideoScrapingsServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Scrape(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_VideoScrapingsServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Scrape': grpc.unary_unary_rpc_method_handler(
                    servicer.Scrape,
                    request_deserializer=scrape__requests__pb2.ScrapeRequest.FromString,
                    response_serializer=scrape__requests__pb2.VideoScrapeResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'VideoScrapings', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class VideoScrapings(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Scrape(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/VideoScrapings/Scrape',
            scrape__requests__pb2.ScrapeRequest.SerializeToString,
            scrape__requests__pb2.VideoScrapeResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
