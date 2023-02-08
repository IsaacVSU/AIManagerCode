import threading
import zmq
import sys
import PlannerProto_pb2 as proto_messages
import AiManager

# Class to handle subscriptions and/or receiving messages from the Planner 
class Subscriber:

    # Constructor
    def __init__(self):
        print("Constructing subscriber")
        self.subscriber_functions = []

    # Determines functions of AiManager that subscribe to protomessages
    def registerSubscribers(self, ai_manager:AiManager):

        # Create subscriber instance of AI manager class
        self.ai_manager = ai_manager
        print("Registering subscribers")

        # Get method names of all subscribers in AiManager with "receive" in function name
        self.subscriber_functions = [method_name for method_name in dir(ai_manager)
                  if callable(getattr(ai_manager, method_name)) and method_name.__contains__("receive")]
        
        # Print registered methods for user error checking
        # If you funciton isn't printed here it will not be called 
        for function_name in self.subscriber_functions:
            print(function_name + " registered")

    # Starts TCP socket and main recieve loop
    def startSubscriber(self):
        event = threading.Event()
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("tcp://127.0.0.1:8886")
        socket.subscribe("")

        try:
            t = threading.Thread(name="recvr-thread", target=self.recvloop, args=[socket, event])
            t.start()

            while t.is_alive():
                t.join(1)
        except KeyboardInterrupt:
            event.set()
            print("Process terminated...")
            sys.exit()

    # Receives messages from the Planner and passes them to related functions in AiManager
    def recvloop(self, socket, event):
        while not event.is_set():
            print("Waiting to recv.")  

            #  On each message recvd, deserialize the message bytes into a MsgContainerPb
            msg = socket.recv()
            serialized = proto_messages.MsgContainerPb()
            serialized.ParseFromString(msg)

            msgType = serialized.Header.ContentType
            print(f"Received a message of type: {msgType}")

            if hasattr(proto_messages, msgType):
                for function in self.subscriber_functions:
                    if function.__contains__(msgType):
                        unpacked = getattr(proto_messages, serialized.Header.ContentType)()
                        serialized.Content.Unpack(unpacked)
                        getattr(self.ai_manager, function)(unpacked)



            
