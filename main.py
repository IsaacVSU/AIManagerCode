# To ensure proper functionality, ensure these versions are used for protobuf and pyzmq
# pip install protobuf==3.20.0
# pip install pyzmq==24.0.0
# Developed on python 3.10.9

from publisher import Publisher
from subscriber import Subscriber
from AiManager import AiManager

if __name__ == '__main__':
    print("Initializing AI client")
    with open("output.txt", 'w') as f1:
        f1.write("TrackID, ThreatID, ThreatRelationship, LLE, PositionX, PositionY, PositionZ, VelocityX, VelocityY, VelocityZ")
    with open("assets.txt", "w") as f2:
        f2.write("asset.AssetName,asset.isHVU,asset.health,asset.PositionX,asset.PositionY,asset.PositionZ,asset.Lle, asset.weapons")
    #Initialize Publisher
    publisher = Publisher()

    #Initialize Subscriber
    subscriber = Subscriber()

    #Initialize AiManager
    ai_manager = AiManager(publisher)

    #Register subscriber functions of Ai manager and begin listening for messages
    subscriber.registerSubscribers(ai_manager)
    subscriber.startSubscriber()