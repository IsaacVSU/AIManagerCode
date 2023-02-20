#Imports
from PlannerProto_pb2 import ScenarioConcludedNotificationPb, ScenarioInitializedNotificationPb     #Scenario start/end notifications
from PlannerProto_pb2 import ErrorPb                                            #Error messsage if scenario fails
from PlannerProto_pb2 import StatePb, AssetPb, TrackPb                          #Simulation state information
from PlannerProto_pb2 import OutputPb, ShipActionPb,  WeaponPb
from publisher import Publisher
import math
import time
import numpy as np

# VSU team notes:
# https://vsu.zoom.us/rec/share/fp_Ty-X-pI2QNBWHQHynJAI1rKs0pqSctEDgPZY53vF4UIFYoZKkOPp0MpIysKUx.oeq8UXnMa1TOkpG0
# (1) if action has incorrect target id, weapon fire fail. same if incorrect asset name and weapon name
# (2) fire the same weapon (of the same ship) twice in the same loop will have the second shot fail, so only one shot a time per ship
# (3) canon is > 2 times faster than chain shot,


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
        self.missile = 8
        self.newobs = False
        self.last_msg = None
        self.done = False
        self.use_myai = False
        self.enemyShipsID_curr = [] # list of the TrackId of enemy missile
        self.enemyPositions_curr=[]
        self.friendlyShips_curr = [] # list of names of friendly ship
        self.friendlyPositions_curr = [] # xy position of friednly ship, 
        self.enemyShipsName_curr = []

        self.friendlyHealths_curr = [] # list of health of friendly ship
        self.new_obs_flag = False
        self.info = ""
        self.ai_callback = None
    
    # wang ai callback is called in receivedStatePb 
    def set_aicallback(self, aicallback):
        self.ai_callback = aicallback

### a switch to decide if myai action should be used, assume that the action is already be putin to 
### self.aiaction_outputmessg
    def set_myai(self, myai=True):
        self.use_myai = myai

#### convert the last state message to the list of variables, and return some
### varibles to caller
###
    def get_stateandresult(self):
        #self.new_obs_flag = False
        self.enemyShipsID_curr = []
        self.enemyPositions_curr=[]
        self.fridenlyShips_curr = []
        self.enemyShipsName_curr = []
        for track in self.last_msg.Tracks:
            x1 = track.PositionX
            y1 = track.PositionY
            z1 = track.PositionZ
            if track.ThreatRelationship=='Hostile':
                self.enemyShipsName_curr.append(track.ThreatId)
                self.enemyShipsID_curr.append(track.TrackId)
                self.enemyPositions_curr.append([x1, y1] )
        for asset in self.last_msg.assets:
            if(asset.AssetName=="Galleon_REFERENCE_SHIP"):
                continue
            x0 = asset.PositionX
            y0 = asset.PositionY
            z0 = asset.PositionZ
            health = asset.health
            self.friendlyShips_curr.append(asset.AssetName)
            self.friendlyPositions_curr.append([x0, y0] )
            self.friendlyHealths_curr.append(health )

        self.obs=np.array(self.enemyPositions_curr)    
        self.award = self.last_msg.score

        return self.obs, self.award, self.done, self.info

### convert ai action to the action message and save for use
### action[0] = index of target, must be within enemyship list 0~m-1
### action[1] = myship id, 0-~n-1
### action [2] = weapon type, 0 for "Cannon_System", 1 for "Chainshot_System"
### AI clients are permitted one action, per ship, per time interval
### ship killed by enemy will be removed from msg.assets
    def do_aiaction(self, action):
        print("********do_aiaction************")
        print(self.enemyShipsID_curr)
        print(self.enemyPositions_curr)
        print("action[0] : ", action[0], " enemy #: ", len(self.enemyShipsID_curr))
        if len(self.enemyShipsID_curr)==0:
            print("no enemy, return")
            return        
        self.new_aiaction_flag = True
        self.new_aiaction = action
        self.ai_output_message: OutputPb = OutputPb()
        # ShipActionPb's are built using the same sytax as the printStateInfo function
        # self.missile -= 1
        ship_action: ShipActionPb = ShipActionPb()

        if action[0] >= len(self.enemyShipsID_curr) or action[1] >= len(self.friendlyShips_curr):
            print("do_aiaction: bad action[] values")
            return
        assert action[0] <= len(self.enemyShipsID_curr)
        assert action[1] <= len(self.friendlyShips_curr)
        
        ship_action.TargetId = self.enemyShipsID_curr[action[0]]
        ship_action.AssetName = self.friendlyShips_curr[action[1]]
        ship_action.weapon = "Chainshot_System" if action[2] ==1 else "Cannon_System"
        # As stated, shipActions go into the OutputPb as a list of ShipActionPbs
        self.ai_output_message.actions.append(ship_action)

    # Is passed StatePb from Planner
    def receiveStatePb(self, msg:StatePb):

        # Call function to print StatePb information
        #self.printStateInfo(msg)

        self.new_obs_flag = True
        self.last_msg = msg
        self.info =  " Time: " + str(msg.time)  + " with score: " + str(msg.score)
        threats_obs, reward, done, info = self.get_stateandresult()
        if not self.ai_callback is None:
            self.ai_action_0 = self.ai_callback(threats_obs, reward,done,info, self.enemyShipsName_curr)
            self.do_aiaction(self.ai_action_0)
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
        self.done = True
        self.info = "Ended Run: " + str(msg.sessionId) + " with score: " + str(msg.score)

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
        assetShips = []
        enemyPositions = []
        assetPositions = []
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
                
                if track.ThreatRelationship=='Hostile':
                    enemyShips.append(track.TrackId)
                    enemyPositions.append([x1, y1, z1] )
                f1.write(f"\n{self.count}, {track.TrackId} , {track.ThreatId}, {track.ThreatRelationship}, {track.Lle}, {round(track.PositionX,3)}, {round(track.PositionY,3)}, {round(track.PositionZ,3)}, {round(track.VelocityX,3)}, {round(track.VelocityY,3)}, {round(track.VelocityZ,3)}")
        with open("assets.txt", 'a') as f2:
            for asset in msg.assets:
                if(asset.AssetName=="Galleon_REFERENCE_SHIP"):
                    continue
                x0 = asset.PositionX
                y0 = asset.PositionY
                z0 = asset.PositionZ
                assetShips.append(asset.AssetName)
                assetPositions.append([x0, y0, z0] )
                f2.write(f"\n{self.count}, {asset.AssetName}, {asset.isHVU}, {asset.health}, {round(asset.PositionX,3)}, {round(asset.PositionY,3)}, {round(asset.PositionZ,3)}, {asset.Lle}, {asset.weapons}")
        # ShipActionPb's go into an OutputPb message

        distanceB = 100000 #distance(x0,y0,z0, x1, y1, z1)
        for enemypos in enemyPositions:
            for assetpos in assetPositions:
                dist2 = distance(enemypos[0],enemypos[1], enemypos[2], assetpos[0], assetpos[1], assetpos[2])
                if dist2 < distanceB:
                    distanceB = dist2
        print("-_- minimum distance")
        print(distanceB)
        print(self.missile)
        output_message: OutputPb = OutputPb()
        # ShipActionPb's are built using the same sytax as the printStateInfo function
        if distanceB<20000 and self.missile > 0 and len(enemyShips) != 0: #distance has to be compared to the millions
            print("Firing!", enemyShips)
            self.missile -= 1
            ship_action: ShipActionPb = ShipActionPb()
            ship_action.TargetId = enemyShips[0] #3 # this should be one of the valid enemy trackId
            ship_action.AssetName = assetShips[0] # "HVU_Galleon_0"
            ship_action.weapon = "Cannon_System" # or "Cannon_System"
        # As stated, shipActions go into the OutputPb as a list of ShipActionPbs
            output_message.actions.append(ship_action)
            if len(enemyShips) >1 and len(assetShips) >1:
                print("Firing! 2nd shot!")
                self.missile -= 1
                ship_action2: ShipActionPb = ShipActionPb()
                ship_action2.TargetId = enemyShips[1] # enemyShips[0] #3 # this should be one of the valid enemy trackId
                ship_action2.AssetName = assetShips[1] # "HVU_Galleon_0"
                ship_action2.weapon = "Chainshot_System" # or "Cannon_System"
                output_message.actions.append(ship_action2)

        #wang this is where we decide to use ai action or regular action
        if self.use_myai:
            output_message = self.ai_output_message
        return output_message
    # Function to print state information and provide syntax examples for accessing protobuf messags
#


