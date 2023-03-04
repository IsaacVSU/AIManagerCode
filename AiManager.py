# ez
# Imports
from PlannerProto_pb2 import ScenarioConcludedNotificationPb, \
    ScenarioInitializedNotificationPb  # Scenario start/end notifications
from PlannerProto_pb2 import ErrorPb  # Error messsage if scenario fails
from PlannerProto_pb2 import StatePb, AssetPb, TrackPb  # Simulation state information
from PlannerProto_pb2 import OutputPb, ShipActionPb, WeaponPb
from publisher import Publisher
import math
import time
import numpy as np


# VSU team notes:
# https://vsu.zoom.us/rec/share/fp_Ty-X-pI2QNBWHQHynJAI1rKs0pqSctEDgPZY53vF4UIFYoZKkOPp0MpIysKUx.oeq8UXnMa1TOkpG0
# (1) if action has incorrect target id, weapon fire fail. same if incorrect asset name and weapon name
# (2) fire the same weapon (of the same ship) twice in the same loop will have the second shot fail, so only one shot a time per ship
# (3) canon is > 2 times faster than chain shot,
# (4) score: canon -400 per shot, chainshot -200 per shot,
# (5) score: take a hit -2000, kill one enemy +600
# (6) each ship weapon is limited, so need to cound how many shot remaining in each ship when fire.


# This class is the center of action for this example client.  Its has the required functionality
# to receive data from the Planner and send actions back.  Developed AIs can be written directly in here or
# this class could be used toolbox that a more complex AI classes reference.

# The word "receive" is protected in this class and should NOT be used in function names
# "receive" is used to notify the subscriber that "this method wants to receive a proto message"

# The second part of the function name is the type of proto message it wants to receive, thus proto
def distance(x0, y0, z0, x1, y1, z1):
    return math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2)


# message names are also protected
class AiManager:

    # Constructor
    def __init__(self, publisher: Publisher):
        print("Constructing AI Manager")
        self.ai_pub = publisher
        self.count = 0
        self.missile = 8
        self.newobs = False
        self.last_msg = None
        self.done = False
        self.use_myai = False
        self.enemyShipsID_curr = []  # list of the TrackId of enemy missile
        self.enemyPositions_curr = []
        self.friendlyShips_curr = []  # list of names of friendly ship
        self.friendlyPositions_curr = []  # xy position of friednly ship,
        self.enemyShipsName_curr = []

        self.friendlyHealths_curr = []  # list of health of friendly ship
        self.fired_shots = {}  # dict of fired shot, used in alg2 so no double shot at same target
        self.new_obs_flag = False
        self.info = ""
        self.ai_callback = None
        self.enemiesx1y1 = []
        self.enemyiesx2y1 = []
        self.assetShips = dict()
        self.enemyToFireAt = []
        self.hvu = -1
        self.seenMissiles = []
        self.enemyTargets = dict()
        self.missilesDestroyedPerShip = dict()
        self.timer = 0
        self.minDistanceToEnemy = 10000000000


    def reset(self):
        if self.done:
            print("Constructing AI Manager")
            # self.ai_pub = publisher
            self.count = 0
            self.missile = 8
            self.newobs = False
            self.last_msg = None
            self.done = False
            self.use_myai = False
            self.enemyShipsID_curr = []  # list of the TrackId of enemy missile
            self.enemyPositions_curr = []
            self.friendlyShips_curr = []  # list of names of friendly ship
            self.friendlyPositions_curr = []  # xy position of friednly ship,
            self.enemyShipsName_curr = []
            self.friendlyHealths_curr = []  # list of health of friendly ship
            self.fired_shots = {}  # dict of fired shot, used in alg2 so no double shot at same target
            self.new_obs_flag = False
            self.info = ""
            self.ai_callback = None
            self.enemiesx1y1 = []
            self.enemyiesx2y1 = []
            self.assetShips = dict()
            self.enemyToFireAt = []
            self.hvu = -1
            self.seenMissiles = []
            self.enemyTargets = dict()
            self.missilesDestroyedPerShip = dict()
            self.timer = 0
            self.minDistanceToEnemy = 10000000000


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
        # self.new_obs_flag = False
        self.enemyShipsID_curr = []
        self.enemyPositions_curr = []
        self.fridenlyShips_curr = []
        self.enemyShipsName_curr = []
        for track in self.last_msg.Tracks:
            x1 = track.PositionX
            y1 = track.PositionY
            z1 = track.PositionZ
            if track.ThreatRelationship == 'Hostile':
                self.enemyShipsName_curr.append(track.ThreatId)
                self.enemyShipsID_curr.append(track.TrackId)
                self.enemyPositions_curr.append([x1, y1])
        for asset in self.last_msg.assets:
            if (asset.AssetName == "Galleon_REFERENCE_SHIP"):
                continue
            x0 = asset.PositionX
            y0 = asset.PositionY
            z0 = asset.PositionZ
            health = asset.health
            self.friendlyShips_curr.append(asset.AssetName)
            self.friendlyPositions_curr.append([x0, y0])
            self.friendlyHealths_curr.append(health)

        self.obs = np.array(self.enemyPositions_curr)
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
        print(type(action))
        print(self.enemyShipsID_curr)
        print(self.enemyPositions_curr)
        print("action[0] : ", action[0], " enemy #: ", len(self.enemyShipsID_curr))
        if len(self.enemyShipsID_curr) == 0:
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
        print("*********************************")
        print("action: ")
        print(action)
        print("*********************************")
        ship_action.TargetId = self.enemyShipsID_curr[action[0]]
        ship_action.AssetName = self.friendlyShips_curr[action[1]]
        ship_action.weapon = "Chainshot_System" if action[2] == 1 else "Cannon_System"
        # As stated, shipActions go into the OutputPb as a list of ShipActionPbs
        self.ai_output_message.actions.append(ship_action)

    # Is passed StatePb from Planner
    def receiveStatePb(self, msg: StatePb):

        # Call function to print StatePb information
        # self.printStateInfo(msg)

        self.new_obs_flag = True
        self.last_msg = msg
        self.info = " Time: " + str(msg.time) + " with score: " + str(msg.score)
        threats_obs, reward, done, info = self.get_stateandresult()
        if not self.ai_callback is None:
            self.ai_action_0 = self.ai_callback(threats_obs, reward, done, info, self.enemyShipsName_curr)
            self.do_aiaction(self.ai_action_0)
        # Call function to show example of building an action
        output_message = self.createActions(msg)
        self.reset()
        print("output_message", output_message)

        # To advance in step mode, its required to return an OutputPb
        self.ai_pub.publish(output_message)
        # self.ai_pub.publish(OutputPb())

    # This method/message is used to notify of new scenarios/runs
    def receiveScenarioInitializedNotificationPb(self, msg: ScenarioInitializedNotificationPb):
        print("Scenario run: " + str(msg.sessionId))

    # This method/message is used to nofify that a scenario/run has ended
    def receiveScenarioConcludedNotificationPb(self, msg: ScenarioConcludedNotificationPb):
        print("Ended Run: " + str(msg.sessionId) + " with score: " + str(msg.score))
        self.done = True
        self.info = "Ended Run: " + str(msg.sessionId) + " with score: " + str(msg.score)

    def printStateInfo(self, msg: StatePb):
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
            for weapon in asset.weapons:
                print("8: ", weapon.Quantity)
            # print("weapons ", type(asset.weapons)) #'google.protobuf.pyext._message.RepeatedCompositeContainer'>
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

    def action_alg5(self, enemyShips, enemyPositions, assetShips, assetPositions, assetWeapons, msg):

        def sortByTime(elem):
            print(enemyShips, elem)
            enemyPos = enemyPositions[enemyShips.index(elem[0])]
            shipPos = assetPositions[elem[1]]
            dis = distance(enemyPos[0], enemyPos[1], enemyPos[2], 
                            shipPos[0], shipPos[1], shipPos[2])
            vel = 0
            for track in msg.Tracks:
                if track.TrackId == elem[0]:
                    vel = math.sqrt(track.VelocityX**2 + track.VelocityY**2 + track.VelocityZ**2)
                    break
            return dis / vel
        
        def willConnect(target_ship, origin_ship, missileType, enemy):
            enemyPos = enemyPositions[enemyShips.index(enemy)]
            shipPos = assetPositions[target_ship]
            dis_to_ship = distance(enemyPos[0], enemyPos[1], enemyPos[2], shipPos[0], shipPos[1], shipPos[2])
            for track in msg.Tracks:
                if track.TrackId == enemy:
                    vel_inc = math.sqrt(track.VelocityX**2 + track.VelocityY**2 + track.VelocityZ**2)
                    break
            if missileType == "Chainshot_System":
                vel_out = 343
            else:
                vel_out = 972
            shipPos = assetPositions[origin_ship]
            dis_to_missile = distance(enemyPos[0], enemyPos[1], enemyPos[2], shipPos[0], shipPos[1], shipPos[2])
            time_to_impact = dis_to_ship/vel_inc
            time_to_intercept = dis_to_missile/(vel_inc+vel_out)

            return time_to_intercept < time_to_impact
            

        self.timer += 1
        newMissiles = {enemyShips[i]: i for i in range(len(enemyShips)) if enemyShips[i] not in self.seenMissiles}
        print('NEW MISSILES', newMissiles)
        output_message: OutputPb = OutputPb()
        
        if len(self.assetShips) == 0:
            for i in range(len(assetShips)):  # Creates dictionary from assetShips {1 (ship ID): [], ...}
                self.assetShips[i] = []
                if assetShips[i][0:3] == 'HVU':
                    self.hvu = i  # Stores HVU ship
                    # assetShips.insert(0, assetShips.pop(i))
                    # assetPositions.insert(0, assetPositions.pop(i))
                    # break
            if self.hvu != -1:  # Reorders dict so that the HVU ship is first, only reorders if necessary
                newAssetShips = {}
                newAssetShips[self.hvu] = []
                for i in range(len(assetShips)):
                    if i != self.hvu:
                        newAssetShips[i] = []
                self.assetShips = newAssetShips
        print("timer", self.timer)
        # if len(newMissiles) != 0 and self.timer%10 == 9:
        #     for enemy in newMissiles:
        #         asset = 0
        #         minDis = 100000000000
        #         for j in range(len(assetPositions)):
        #             dist2 = distance(enemyPositions[newMissiles[enemy]][0], enemyPositions[newMissiles[enemy]][1], enemyPositions[newMissiles[enemy]][2], 
        #                              assetPositions[j][0], assetPositions[j][1], assetPositions[j][2])
        #             # self.minDistanceToEnemy = min(self.minDistanceToEnemy, dist2)
        #             if dist2 < minDis:
        #                 minDis = dist2
        #                 asset = j
        #         if asset not in self.assetShips:
        #             self.assetShips[asset] = []
        #         self.assetShips[asset].append(enemy)
        #         self.enemyTargets[enemy] = asset
        #         self.seenMissiles.append(enemy)

        
        for enemy in newMissiles:
            asset = 0
            minDis = 100000000000
            for j in range(len(assetPositions)):
                dist2 = distance(enemyPositions[newMissiles[enemy]][0], enemyPositions[newMissiles[enemy]][1], enemyPositions[newMissiles[enemy]][2], 
                                assetPositions[j][0], assetPositions[j][1], assetPositions[j][2])
                # self.minDistanceToEnemy = min(self.minDistanceToEnemy, dist2)
                if dist2 < minDis:
                    minDis = dist2
                    asset = j
            if asset not in self.assetShips:
                self.assetShips[asset] = []
            if minDis < 40000 or (self.timer == 30 or (self.timer > 30 and self.timer%15 == 0)):
                self.assetShips[asset].append(enemy)
                self.enemyTargets[enemy] = asset
                self.seenMissiles.append(enemy)



        
        for ship in self.assetShips:
            if ship < len(assetPositions):
                enemies = [(i, ship) for i in self.assetShips[ship] if i in enemyShips]
                enemies.sort(key=sortByTime)
                self.assetShips[ship] = [i[0] for i in enemies]


        # if self.minDistanceToEnemy > 50000:  # Only starts firing if missiles are 50000 away - don't want to fire too early in case not all missiles have fired yet
        #     print('SHIPS TOO FAR AWAY - DON\'T ENGAGE YET', self.minDistanceToEnemy)
        #     print("timer", self.timer)
        #     return output_message

        print('NORMAL ASSET SHIPS: ', assetShips)
        print('ASSET SHIPS: ', self.assetShips)

        orderToFireAt = [[], [], [], []]
        current = 0
        for i in range(len(self.enemyToFireAt)):
            if self.enemyToFireAt[i][1] != self.hvu and current == 0:
                current = 1
            elif self.enemyToFireAt[i][1] == self.hvu and current == 1:
                current = 2
            elif self.enemyToFireAt[i][1] != self.hvu and current == 2:
                current = 3
            orderToFireAt[current].append(self.enemyToFireAt[i])
            

        weaponsRemaining = sum([i[0] + i[1] for i in assetWeapons])  # calculates number of remaining weapons
        for ship in self.assetShips:  # first priority is to make sure that no ship dies, starting with the HVU ship
            if weaponsRemaining > 0:
                while len(self.assetShips[ship]) >= 4:
                    if ship == self.hvu:
                        orderToFireAt[0].append((self.assetShips[ship].pop(0), ship))
                    else:
                        orderToFireAt[1].append((self.assetShips[ship].pop(0), ship))
                    weaponsRemaining -= 1
                    if weaponsRemaining == 0:
                        break

        # NEED TO EXHAUST REMAINING CHAINSHOTS/CANNONS
        for ship in self.assetShips:  # then we fire the rest of our weapons at remaining missiles, starting with the HVU ship again
            if weaponsRemaining > 0:
                while len(self.assetShips[ship]) > 0:
                    if ship == self.hvu:
                        orderToFireAt[2].append((self.assetShips[ship].pop(0), ship))
                    else:
                        orderToFireAt[3].append((self.assetShips[ship].pop(0), ship))
                    weaponsRemaining -= 1
                    if weaponsRemaining == 0:
                        break

        self.enemyToFireAt = []
        
        for order in orderToFireAt:
            order.sort(key=sortByTime)
        for order in orderToFireAt:
            self.enemyToFireAt.extend(order)
        print("enemies to fire at", self.enemyToFireAt)
        print("enemy targets", self.enemyTargets)


        if len(self.enemyToFireAt) == 0:
            print('NO ENEMIES TO FIRE AT')
            return output_message

        enemy = self.enemyToFireAt.pop(0)[0]  # Only 1 enemy is destroyed per tick
        ship_action2: ShipActionPb = ShipActionPb()
        ship_action2.TargetId = enemy
        if assetWeapons[self.enemyTargets[enemy]][1] > 0:
            ship_action2.AssetName = assetShips[self.enemyTargets[enemy]]
            ship_action2.weapon = "Chainshot_System"
            print("alg2 dbg firing: ", ship_action2)
            output_message.actions.append(ship_action2)
            return output_message
        else:
            for i in range(len(assetWeapons)):  # Looks through weapons to see how many is left, fires chainshots before cannons (assuming that all weapons are exhausted)
                if assetWeapons[i][1] > 0 and willConnect(self.enemyTargets[enemy], i, "Chainshot_System", enemy):
                    ship_action2.AssetName = assetShips[i]
                    ship_action2.weapon = "Chainshot_System"
                    print("alg2 dbg firing: ", ship_action2)
                    output_message.actions.append(ship_action2)
                    return output_message
        if assetWeapons[self.enemyTargets[enemy]][0] > 0:
            ship_action2.AssetName = assetShips[self.enemyTargets[enemy]]
            ship_action2.weapon = "Cannon_System"
            print("alg2 dbg firing: ", ship_action2)
            output_message.actions.append(ship_action2)
            return output_message
        else:
            for i in range(len(assetWeapons)):  # Looks through weapons to see how many is left, fires chainshots before cannons (assuming that all weapons are exhausted)
                if assetWeapons[i][0] > 0 and willConnect(self.enemyTargets[enemy], i, "Cannon_System", enemy):
                    ship_action2.AssetName = assetShips[i]
                    ship_action2.weapon = "Cannon_System"
                    print("alg2 dbg firing: ", ship_action2)
                    output_message.actions.append(ship_action2)
                    return output_message
    
        print('NO WEAPONS LEFT OR IMPOSSIBLE TO DEFEND: COULD NOT FIRE')
        return output_message

    # def action_alg4(self, enemyShips, enemyPositions, assetShips, assetPositions, assetWeapons):
    #     print("enemyships", enemyShips)
    #     self.timer += 1
    #     maxdist = 0
    #     for i in assetPositions:
    #         for j in assetPositions:
    #             maxdist = max(maxdist, distance(i[0], i[1], i[2], j[0], j[1], j[2]))
    #     newMissiles = {enemyShips[i]: i for i in range(len(enemyShips)) if enemyShips[i] not in self.seenMissiles}
    #     print('NEW MISSILES', newMissiles)
    #     output_message: OutputPb = OutputPb()

    #     if len(self.assetShips) == 0:
    #         for i in range(len(assetShips)):  # Creates dictionary from assetShips {1 (ship ID): [], ...}
    #             self.assetShips[i] = []
    #             if assetShips[i][0:3] == 'HVU':
    #                 self.hvu = i  # Stores HVU ship
    #         if self.hvu != -1:  # Reorders dict so that the HVU ship is first, only reorders if necessary
    #             newAssetShips = {}
    #             newAssetShips[self.hvu] = []
    #             for i in range(len(assetShips)):
    #                 if i != self.hvu:
    #                     newAssetShips[i] = []
    #             self.assetShips = newAssetShips

    #     if len(newMissiles) != 0 and self.timer%15 == 14:
    #         for enemy in newMissiles:
    #             asset = 0
    #             minDis = 100000000000
    #             for j in range(len(assetPositions)):
    #                 dist2 = distance(enemyPositions[newMissiles[enemy]][0], enemyPositions[newMissiles[enemy]][1],
    #                                  enemyPositions[newMissiles[enemy]][2], assetPositions[j][0], assetPositions[j][1],
    #                                  assetPositions[j][2])
    #                 self.minDistanceToEnemy = min(self.minDistanceToEnemy, dist2)
    #                 if dist2 < minDis:
    #                     minDis = dist2
    #                     asset = j
    #             if asset not in self.assetShips:
    #                 self.assetShips[asset] = []
    #             self.assetShips[asset].append(enemy)
    #             self.enemyTargets[enemy] = asset
    #             self.seenMissiles.append(enemy)

    #     if self.minDistanceToEnemy > 50000:  # Only starts firing if missiles are 50000 away - don't want to fire too early in case not all missiles have fired yet
    #         print('SHIPS TOO FAR AWAY - DON\'T ENGAGE YET', self.minDistanceToEnemy)
    #         return output_message

    #     print('ASSET SHIPS: ', self.assetShips)

    #     weaponsRemaining = sum([i[0] + i[1] for i in assetWeapons])  # calculates number of remaining weapons
    #     for ship in self.assetShips:  # first priority is to make sure that no ship dies, starting with the HVU ship
    #         if weaponsRemaining > 0:
    #             while len(self.assetShips[ship]) >= 4:
    #                 self.enemyToFireAt.append(self.assetShips[ship].pop(0))
    #                 weaponsRemaining -= 1
    #                 if weaponsRemaining == 0:
    #                     break
    #     # NEED TO EXHAUST REMAINING CHAINSHOTS/CANNONS
    #     for ship in self.assetShips:  # then we fire the rest of our weapons at remaining missiles, starting with the HVU ship again
    #         if weaponsRemaining > 0:
    #             while len(self.assetShips[ship]) > 0:
    #                 self.enemyToFireAt.append(self.assetShips[ship].pop(0))
    #                 weaponsRemaining -= 1
    #                 if weaponsRemaining == 0:
    #                     break

    #     if len(self.enemyToFireAt) == 0:
    #         print('ALL ENEMY DESTROYED')
    #         return output_message

    #     enemy = self.enemyToFireAt.pop(0)  # Only 1 enemy is destroyed per tick
    #     ship_action2: ShipActionPb = ShipActionPb()
    #     ship_action2.TargetId = enemy
    #     if assetWeapons[self.enemyTargets[enemy]][1] > 0:
    #         ship_action2.AssetName = assetShips[self.enemyTargets[enemy]]
    #         ship_action2.weapon = "Chainshot_System"
    #         print("alg2 dbg firing: ", ship_action2)
    #         output_message.actions.append(ship_action2)
    #         return output_message
    #     elif assetWeapons[self.enemyTargets[enemy]][0] > 0:
    #         ship_action2.AssetName = assetShips[self.enemyTargets[enemy]]
    #         ship_action2.weapon = "Cannon_System"
    #         print("alg2 dbg firing: ", ship_action2)
    #         output_message.actions.append(ship_action2)
    #         return output_message
    #     else:
    #         for i in range(
    #                 len(assetWeapons)):  # Looks through weapons to see how many is left, fires chainshots before cannons (assuming that all weapons are exhausted)
    #             if assetWeapons[i][1] > 0:
    #                 ship_action2.AssetName = assetShips[i]
    #                 ship_action2.weapon = "Chainshot_System"
    #                 print("alg2 dbg firing: ", ship_action2)
    #                 output_message.actions.append(ship_action2)
    #                 return output_message
    #             elif assetWeapons[i][0] > 0:
    #                 ship_action2.AssetName = assetShips[i]
    #                 ship_action2.weapon = "Cannon_System"
    #                 print("alg2 dbg firing: ", ship_action2)
    #                 output_message.actions.append(ship_action2)
    #                 return output_message
    #     print('NO WEAPONS LEFT: COULD NOT FIRE')
    #     return output_message

    # Example function for building OutputPbs, returns OutputPb
    # Try:
    # Save the enemy list and enemy list into a file
    # simple file format probably in a MD file or smth
    # [x,y,z] same line
    # round the numbers to 3 decimal points
    def createActions(self, msg: StatePb):
        enemyShips = []
        assetShips = []
        enemyPositions = []
        assetPositions = []
        assetWeapons = []  # nx2 each ship has two weapon types, this list save the number of  remaining for each ship's weapon
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

                if track.ThreatRelationship == 'Hostile':
                    enemyShips.append(track.TrackId)
                    enemyPositions.append([x1, y1, z1])
                f1.write(
                    f"\n{self.count}, {track.TrackId} , {track.ThreatId}, {track.ThreatRelationship}, {track.Lle}, {round(track.PositionX, 3)}, {round(track.PositionY, 3)}, {round(track.PositionZ, 3)}, {round(track.VelocityX, 3)}, {round(track.VelocityY, 3)}, {round(track.VelocityZ, 3)}")
        with open("assets.txt", 'a') as f2:
            for asset in msg.assets:
                if (asset.AssetName == "Galleon_REFERENCE_SHIP"):
                    continue
                x0 = asset.PositionX
                y0 = asset.PositionY
                z0 = asset.PositionZ

                wn = []  # weapon number list
                for weapon in asset.weapons:
                    print('weapon checking ', weapon)
                    wn.append(weapon.Quantity)
                assetShips.append(asset.AssetName)
                assetPositions.append([x0, y0, z0])
                assetWeapons.append(wn)
                f2.write(
                    f"\n{self.count}, {asset.AssetName}, {asset.isHVU}, {asset.health}, {round(asset.PositionX, 3)}, {round(asset.PositionY, 3)}, {round(asset.PositionZ, 3)}, {asset.Lle}, {asset.weapons}")

        output_message = self.action_alg5(enemyShips, enemyPositions, assetShips, assetPositions, assetWeapons, msg)
        print("*********************************")
        print("assetWeapons")
        print(assetWeapons)
        print("*********************************")
        #        output_message = self.action_alg1(enemyShips, enemyPositions, assetShips, assetPositions, assetWeapons)
        # wang this is where we decide to use ai action or regular action
        if self.use_myai:
            output_message = self.ai_output_message
        return output_message
    # Function to print state information and provide syntax examples for accessing protobuf messags
#

