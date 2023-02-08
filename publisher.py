
from google.protobuf import message, any_pb2
import zmq

from zmq.sugar.frame import Message
import PlannerProto_pb2 as proto_messages

# Class to send messages to the Planner
class Publisher:
    
    # Constructor
    def __init__(self):
        print("Constructing publisher")
        self.msgNum = 0
        context = zmq.Context()
        self.socket = context.socket(zmq.PUB)
        self.socket.connect("tcp://127.0.0.1:8885")

    # Puts message into proper protobuf container
    def package(self, msg: Message):
        simpleName = type(msg).__name__
        container:proto_messages.MsgContainerPb = proto_messages.MsgContainerPb()
        header:proto_messages.MsgHeaderPb = container.Header
        header.Id = self.msgNum
        self.msgNum+=1
        header.ContentType = simpleName
        any = container.Content.Pack(msg)
        print(f"Publishing {simpleName}")
        return container

    # Sends message to specified IP and port
    def publish(self, msg: Message):
        container = self.package(msg)
        bytes = container.SerializeToString()
        self.socket.send(bytes)








