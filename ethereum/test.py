#!/usr/bin/env python3

import numpy as np
import sys
import os
curdir = os.path.abspath(os.curdir)
sys.path.extend([curdir, os.path.join(curdir, 'rl-baselines3-zoo'), os.path.join(curdir, 'one-inch-trades')])

import custom_envs

from utils.exp_manager import ExperimentManager
exp_manager = ExperimentManager(
        {},#args,
        'tqc',#args.algo,
        'oit-v1',#env_id,
        'logs',#args.log_folder,
        '',#args.tensorboard_log,
        -1,#args.n_timesteps,
        2,#10000,#args.eval_freq,  # number of steps after which to evaluate the agent
        5,#args.eval_episodes,  # number of episodes to use for evaluation
        2,#-1,#args.save_freq, # save the model every n steps
        {},#args.hyperparams, # overwrite e.g. learning_rate:0.01 train_freq:10
        {},#args.env_kwargs, # kwarguments to the env
        '',#args.trained_agent, # must be valid path to a .zip file
        True,#False,#args.optimize_hyperparameters, # run hyperparameter search
        '.',#args.storage, # db path for distributed optimization
        'oit',#args.study_name, # for distributed optimization
        10,#args.n_trials, # trials for hyperparam optimization
        4,#args.n_jobs, # parallel jobs for hyperparam optimization
        'tpe',#args.sampler, # hyperparam sampler: random, tpe, skopt
        'median',#args.pruner, # hyperparam pruner:  havling, median, none
        10,#n_startup_trials=args.n_startup_trials, # trials before optuna sampler
        20,#n_evaluations=args.n_evaluations, # hyperparam optimization evaluations
        True,#truncate_last_trajectory=args.truncate_last_trajectory,
        '',#uuid_str=uuid_str, # uuid to prevent file race conditions
        np.random.randint(2 ** 32 - 1, dtype='int64').item(),#seed=args.seed,
        -1,#log_interval=args.log_interval,
        True,#save_replay_buffer=args.save_replay_buffer,
        1,#verbose=args.verbose,
        'dummy',#vec_env_type=args.vec_env, # dummy, subproc
)

model = exp_manager.setup_experiment()

# Normal training
if model is not None:
    exp_manager.learn(model)
    exp_manager.save_trained_model(model)
else:
    exp_manager.hyperparameters_optimization()
