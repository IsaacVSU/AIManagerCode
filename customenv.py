import gym
import numpy as np
from gym import spaces
from gym.spaces import Discrete
from gym.spaces import MultiDiscrete
from publisher import Publisher
from subscriber import Subscriber
from AiManager import AiManager
import time

class CustomEnv(gym.Env):
    """Custom Environment that follows gym interface."""

    metadata = {"render.modes": ['console']} 
    #metadata = {"render.modes": ["human"]} 
    LEFT = 0
    RIGHT = 1
    THREADID_SEL = 30        
    ASSETID_SEL = 5
    WEAPON_SEL = 2
    
    #action tuple (threatid, assetid, weapon_id), ai current limitation fire one weapon at each interval,
    #             regular algorithm can generate action for all ships in each interval

   
    ENEMy_XY = 2 
    def __init__(self, threat_size = 10, publisher=None,subscriber=None, ai_manager=None): #maximum 10 enemy threats
        super().__init__()
 
        # create jcore interface
        print("Initializing AI client")
        with open("output.txt", 'w') as f1:
            f1.write("TrackID, ThreatID, ThreatRelationship, LLE, PositionX, PositionY, PositionZ, VelocityX, VelocityY, VelocityZ")
        with open("assets.txt", "w") as f2:
            f2.write("asset.AssetName,asset.isHVU,asset.health,asset.PositionX,asset.PositionY,asset.PositionZ,asset.Lle, asset.weapons")
        self.publisher = publisher

        self.subscriber = subscriber
        self.ai_manager = ai_manager

        self.threat_size = threat_size
        self.threats_obs = np.zeros((self.threat_size, self.ENEMy_XY)) # this is the observation variable
        # Define action and observation space
        # They must be gym.spaces objects
        # Example when using discrete actions:


        self.action_space = spaces.MultiDiscrete([self.THREADID_SEL, self.ASSETID_SEL, self.WEAPON_SEL])
         #spaces.Discrete(self.N_DISCRETE_ACTIONS)
        # Example for using image as input (channel-first; channel-last also works):
        self.observation_space = spaces.Box(low=0, high=255,
                                            shape=(self.threat_size, self.ENEMy_XY), dtype=np.uint8)

    def step(self, action):
        self.ai_manager.do_aiaction(action)
        while not self.ai_manager.new_obs_flag:
            time.sleep(0.1)
        self.threats_obs, reward, done, info = self.ai_manager.get_stateandresult()

        self.threats_obs = self.threats_obs[:self.threat_size] # limit to 10 as our ai model assume 10x2 obs space
        self.ai_manager.new_obs_flag = False
        print("step: threats_obs= ", self.threats_obs)
        obs=np.zeros((10,2))
        threats_num=len(self.threats_obs)
        if threats_num>0:            
            obs[:threats_num] = self.threats_obs.astype(np.float32)
        print(obs)
        return obs, reward, done, info

    def reset(self):
        #self.agent_pos = self.grid_size - 1
        #np.array([self.agent_pos]).astype(np.float32)

        self.threats_obs = np.zeros((self.threat_size, self.ENEMy_XY))
        return self.threats_obs.astype(np.float32)  # reward, done, info can't be included

    def render(self, mode='console'):
        if mode != 'console':
            raise NotImplementedError()
    # agent is represented as a cross, rest as a dot
        print("." * len(self.threats_obs), end="")
        #print("x", end="")
        #print("." * (self.grid_size - self.agent_pos))        

    def close(self):
       pass 