import gym
import customenv
from customenv import *
from stable_baselines3 import A2C
from publisher import Publisher
from subscriber import Subscriber
from AiManager import AiManager

# env = gym.make("CartPole-v1")
# print("Observation space:", env.observation_space)
# print("Shape:", env.observation_space.shape)
# print("Action space:", env.action_space)
# action = env.action_space.sample()
# print("Sampled action:", action)

# obs = env.reset()
# obs, reward, done, info = env.step(action)
# print(obs.shape, reward, done, info)

def aicallback_func(threats_obs,reward,done,info, threats_IDs):
    global env

    print("aicallback_func ****** enemy #: ", len(threats_obs))
    #print(env.observation_space.shape[0])
    obs_size_aimodel = env.observation_space.shape[0]
    obs=np.zeros((obs_size_aimodel,2)) # 10x2 
    threats_num=len(threats_obs)
    if threats_num>0:
        obs_threat_used = min(threats_num, obs_size_aimodel)            
        obs[:obs_threat_used] = threats_obs[:obs_threat_used].astype(np.float32)
    print(threats_IDs)
    print(obs)
    action=0
    action, _state = model.predict(obs, deterministic=True)
    return action

publisher = Publisher()
subscriber = Subscriber()
ai_manager = AiManager(publisher)
#Register subscriber functions of Ai manager and begin listening for messages
subscriber.registerSubscribers(ai_manager)
subscriber.startSubscriber(blocking=False)

print("customenv...")
env = CustomEnv(threat_size=10, publisher=publisher, subscriber=subscriber, ai_manager=ai_manager)
ai_manager.set_aicallback(aicallback_func)

obs = env.reset()
env.render()

print(env.observation_space)
print(env.action_space)
print(env.action_space.sample())

model = A2C("MlpPolicy", env, verbose=1)
#model.learn(total_timesteps=10_000)

aicallback_func([],0,0,0,0)
vec_env = model.get_env()
obs = vec_env.reset()

for i in range(10):
    action, _state = model.predict(obs, deterministic=True)
    print("test action: ", action)
    obs, reward, done, info =  vec_env.step(action)
    #vec_env.render()