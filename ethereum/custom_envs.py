import gym
import gym.envs.registration
import logging
import math
import numpy as np
import os
import time
import stable_baselines3
from stable_baselines3.common.env_checker import check_env
import sb3_contrib

# this the environment that one_inch_trades assumes
curdir=os.path.abspath(os.curdir)
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'one-inch-trades'))
if 'ETH_PROVIDER_URL' not in os.environ:
    os.environ['ETH_PROVIDER_URL'] = 'https://mainnet.infura.io/v3/27a61c91018d4bbb899154c8e72f9deb'
if 'BASE_ACCOUNT' not in os.environ:
    os.environ['BASE_ACCOUNT'] = '0x000be6292cf63b71909472211fd92e81efa96582'
import one_inch_trades as oit
os.chdir(curdir)

class oitenv(gym.Env):
    def __init__(self, fiat = oit.ethereum, *tokens):
        if not tokens:
            tokens = (oit.mcd_contract_address,)
        tokens = (fiat, *tokens)
        self._fiatidx = 0
        self._tokens = tokens
        self._indices = {token: index for index, token in enumerate(tokens)}
        self._history = []
        self._timepoint = 0
        ntokens = len(self._tokens)
        # ethereum uses uint256s which aren't in numpy
        # we approximate with float64s because float128 can cause issues in gym
        self._balances = np.array([0] * ntokens, dtype=np.float64)
        self._balances[0] = 1000000000000000000
        #self._changes = np.array([0] * ntokens, dtype=np.float64)

        #self._last_observation = None

        # each balance in each currency
        self.observation_space = gym.spaces.Box(-1.0, 1.0, (ntokens*ntokens,), np.float64)
        # amounts to trade
        self.action_space = gym.spaces.Box(-1.0, 1.0, (ntokens*ntokens,), np.float64)
    def quote(self, from_token, to_token, amount):
        #print('quote', from_token, to_token, amount)
        return oit.one_inch_get_quote(from_token, to_token, amount)[0]
    def _observe(self):
        self._timepoint += 1
        print(self._timepoint)
        if self._timepoint <= len(self._history):
            return self._history[self._timepoint - 1]
        while True:
            nonnormalised = np.array([
                 [
                     self.quote(self._tokens[from_token], self._tokens[to_token], int(self._balances[from_token]))
                     for to_token in range(len(self._tokens))
                 ]
                 for from_token in range(len(self._tokens))
            ])
            if len(self._history) and (nonnormalised == self._history[-1]).all():
                time.sleep(1)
                continue
            self._history.append(nonnormalised)
            return nonnormalised
    def normalise_observation(self, observation):
        normalised = observation / observation.sum(axis=0, keepdims=True)
        return normalised.flatten()
    def reset(self):
        # we could store history here, and rewind.
        self._timepoint = 0
        return self.normalise_observation(self._observe())
    def step(self, action_value):
        # process symmetry
        action_value = action_value.reshape((len(self._tokens),len(self._tokens)))
        action_value = (action_value - action_value.T)

        # randomise trade order
        amounts = [*np.ndenumerate(action_value)]
        np.random.shuffle(amounts)

        for tokenpair, amount in amounts:
            from_token, to_token = tokenpair
            if from_token >= to_token:
                continue
            if amount < 0:
                amount = -amount
                from_token, to_token = to_token, from_token
            if amount > 1:
                amount = 1
            from_amount = int(amount * self._balances[from_token])
            if from_amount == 0:
                continue

            self._balances[from_token] -= from_amount
            to_amount = self.quote(self._tokens[from_token], self._tokens[to_token], from_amount) * 0.999
            self._balances[to_token] += to_amount
            #print('trade', amount, from_token, from_amount, to_token, to_amount)
        #print('status', self._balances, self._changes)
        #self._balances += self._changes

        observation = self._observe()
        # scale reward from -1 to 1
        # >1 becomes >0
        # <1 becomes <0
        ## subtract 1
        # 1000% becomes 1
        ### 1000% is 10
        # 0 becomes -1
        reward = np.sum(observation[:, self._fiatidx]) / np.sum(self._history[0][:, self._fiatidx])
        reward = math.log(reward)
        print('reward', reward)
        return self.normalise_observation(observation), reward, False, {}

oit.logger.setLevel(oit.logging.WARNING)
gym.envs.registration.register(
    id='oit-v1',
    entry_point='custom_envs:oitenv',
    max_episode_steps=1000,
    reward_threshold=1.0
)
#env = oitenv(oit.ethereum, oit.mcd_contract_address)
#check_env(env)
#action = env.action_space.sample()
#print(action)
#print(env.step(action))
# use SAC, TD3, or TQC (tqc is in sb3_contrib)
# RL zoo can train hyperparameters
#model = sb3_contrib.TQC("MlpPolicy", env, verbose=1)
#model.learn(total_timesteps=100)#000)

