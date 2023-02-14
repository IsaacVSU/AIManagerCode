#Imports
from PlannerProto_pb2 import ScenarioConcludedNotificationPb, ScenarioInitializedNotificationPb     #Scenario start/end notifications
from PlannerProto_pb2 import ErrorPb                                            #Error messsage if scenario fails
from PlannerProto_pb2 import StatePb, AssetPb, TrackPb                          #Simulation state information
from PlannerProto_pb2 import OutputPb, ShipActionPb,  WeaponPb
from publisher import Publisher
import math


# This class is the center of action for this example client.  Its has the required functionality 
# to receive data from the Planner and send actions back.  Developed AIs can be written directly in here or
# this class could be used toolbox that a more complex AI classes reference.

# The word "receive" is protected in this class and should NOT be used in function names
# "receive" is used to notify the subscriber that "this method wants to receive a proto message"

# The second part of the function name is the type of proto message it wants to receive, thus proto
def distance(x0, y0, z0, x1, y1, z1):
    return math.sqrt((x1-x0)**2 +(y1-y0)**2 + (z1 - z0)**2)

# message names are also protected
class AiManager:

    # Constructor
    def __init__(self, publisher:Publisher):
        print("Constructing AI Manager")
        self.ai_pub = publisher
        self.count = 0
        self.missile = 1
   
    # Is passed StatePb from Planner
    def receiveStatePb(self, msg:StatePb):

        # Call function to print StatePb information
        self.printStateInfo(msg)

        # Call function to show example of building an action
        output_message = self.createActions(msg)
        print(output_message)

        # To advance in step mode, its required to return an OutputPb
        self.ai_pub.publish(output_message)
        #self.ai_pub.publish(OutputPb())

    # This method/message is used to notify of new scenarios/runs
    def receiveScenarioInitializedNotificationPb(self, msg:ScenarioInitializedNotificationPb):
        print("Scenario run: " + str(msg.sessionId))

    # This method/message is used to nofify that a scenario/run has ended
    def receiveScenarioConcludedNotificationPb(self, msg:ScenarioConcludedNotificationPb):
        print("Ended Run: " + str(msg.sessionId) + " with score: " + str(msg.score))
    def printStateInfo(self, msg:StatePb):
        print("Time: " + str(msg.time))
        print("Score: " + str(msg.score))

        # Accessing asset fields.  Notice that is is simply the exact name as seen 
        # In PlannerProto.proto
        print("Assets:")
        for asset in msg.assets:
            print("1: " + str(asset.AssetName))
            print("2: " + str(asset.isHVU))
            print("3: " + str(asset.health))
            print("4: " + str(asset.PositionX))
            print("5: " + str(asset.PositionY))
            print("6: " + str(asset.PositionZ))
            print("7: " + str(asset.Lle))
            print("8: " + str(asset.weapons))
        print("--------------------")

        # Accessing track information is done the same way.  
        print("Tracks:")
        for track in msg.Tracks:
            print("1: " + str(track.TrackId))
            print("2: " + str(track.ThreatId))
            print("3 " + str(track.ThreatRelationship))
            print("4: " + str(track.Lle))
            print("5: " + str(track.PositionX))
            print("6: " + str(track.PositionY))
            print("7: " + str(track.PositionZ))
            print("8: " + str(track.VelocityX))
            print("9 " + str(track.VelocityY))
            print("10: " + str(track.VelocityZ))
        print("**********************************")
    # Example function for building OutputPbs, returns OutputPb
    #Try:
    #Save the enemy list and enemy list into a file
    #simple file format probably in a MD file or smth
    #[x,y,z] same line
    #round the numbers to 3 decimal points
    def createActions(self, msg:StatePb):
        enemyShips = []
        self.count += 1
        x0 = 0
        y0 = 0
        z0 = 0
        x1 = 0
        y1 = 0
        z1 = 0
        with open("output.txt", 'a') as f1:
            for track in msg.Tracks:
                x1 = track.PositionX
                y1 = track.PositionY
                z1 = track.PositionZ
                enemyShips.append(track.ThreatId)
                f1.write(f"\n{self.count}, {track.TrackId} , {track.ThreatId}, {track.ThreatRelationship}, {track.Lle}, {round(track.PositionX,3)}, {round(track.PositionY,3)}, {round(track.PositionZ,3)}, {round(track.VelocityX,3)}, {round(track.VelocityY,3)}, {round(track.VelocityZ,3)}")
        with open("assets.txt", 'a') as f2:
            for asset in msg.assets:
                if(asset.AssetName=="Galleon_REFERENCE_SHIP"):
                    continue
                x0 = asset.PositionX
                y0 = asset.PositionY
                z0 = asset.PositionZ
                f2.write(f"\n{self.count}, {asset.AssetName}, {asset.isHVU}, {asset.health}, {round(asset.PositionX,3)}, {round(asset.PositionY,3)}, {round(asset.PositionZ,3)}, {asset.Lle}, {asset.weapons}")
        # ShipActionPb's go into an OutputPb message
        distanceB = distance(x0,y0,z0, x1, y1, z1)
        print("-_-")
        print(distanceB)
        print(self.missile)
        output_message: OutputPb = OutputPb()
        # ShipActionPb's are built using the same sytax as the printStateInfo function
        if distanceB<20000 and self.missile > 0 and len(enemyShips) != 0: #distance has to be compared to the millions
            print("Firing!")
            self.missile -= 1
            ship_action: ShipActionPb = ShipActionPb()
            ship_action.TargetId = 3
            ship_action.AssetName = "HVU_Galleon_0"
            ship_action.weapon = "Chainshot_System"
        # As stated, shipActions go into the OutputPb as a list of ShipActionPbs
            output_message.actions.append(ship_action)
        return output_message
    # Function to print state information and provide syntax examples for accessing protobuf messags
#


