import sys
sys.path.append(".")

import numpy as np
from DDPG import *
from main import *
import os.path
from Environment import Environment
from shield import Shield
import argparse


def carplatoon(learning_method, number_of_rollouts, simulation_steps,
        learning_eposides, actor_structure, critic_structure, train_dir,
        nn_test=False, retrain_shield=False, shield_test=False,
        test_episodes=100, retrain_nn=False, safe_training=False, shields=1,
        episode_len=100):

    A = np.matrix([
      [1,0,0,0,0,0,0],
      [0,1,0.1,0,0,0,0],
      [0,0,1,0,0,0,0],
      [0,0,0,1,0.1,0,0],
      [0,0,0,0,1,0,0],
      [0,0,0,0,0,1,0.1],
      [0,0,0,0,0,0,1]
    ])
    B = np.matrix([
      [0.1,0,0,0],
      [0,0,0,0],
      [0.1,-0.1,0,0],
      [0,0,0,0],
      [0,0.1,-0.1,0],
      [0,0,0,0],
      [0,0,0.1,-0.1]
    ])

    #intial state space
    s_min = np.array([[ 19.9],[ 0.9], [-0.1], [ 0.9],[-0.1], [ 0.9], [-0.1]])
    s_max = np.array([[ 20.1],[ 1.1], [ 0.1], [ 1.1],[ 0.1], [ 1.1], [ 0.1]])

    Q = np.identity(7)
    R = 0.0005 * np.identity(4)

    x_min = np.array([[18],[0.5],[-0.35],[0.5],[-1],[0.5],[-1]])
    x_max = np.array([[22],[1.5], [0.35],[1.5],[ 1],[1.5],[ 1]])
    u_min = np.array([[-10.], [-10.], [-10.], [-10.]])
    u_max = np.array([[ 10.], [ 10.], [ 10.], [ 10.]])

    #Coordination transformation
    origin = np.array([[20], [1], [0], [1], [0], [1], [0]])
    s_min -= origin
    s_max -= origin
    x_min -= origin
    x_max -= origin

    env = Environment(A, B, u_min, u_max, s_min, s_max, x_min, x_max, Q, R)

    x_mid = (x_min + x_max) / 2.0

    def shield_reward(x, Q, u, R):
        return -np.matrix([[np.sum(np.abs(x - x_mid))]])

    if retrain_nn:
        args = { 'actor_lr': 0.0001,
             'critic_lr': 0.001,
             'actor_structure': actor_structure,
             'critic_structure': critic_structure, 
             'buffer_size': 1000000,
             'gamma': 0.99,
             'max_episode_len': episode_len,
             'max_episodes': 10000,   # originally 1000
             'minibatch_size': 64,
             'random_seed': 6553,
             'tau': 0.005,
             'model_path': train_dir+"retrained_model.chkp",
             'enable_test': nn_test, 
             'test_episodes': test_episodes,
             'test_episodes_len': 5000}
    else:
        args = { 'actor_lr': 0.0001,
                 'critic_lr': 0.001,
                 'actor_structure': actor_structure,
                 'critic_structure': critic_structure, 
                 'buffer_size': 1000000,
                 'gamma': 0.99,
                 'max_episode_len': episode_len,
                 'max_episodes': learning_eposides,
                 'minibatch_size': 64,
                 'random_seed': 6553,
                 'tau': 0.005,
                 'model_path': train_dir+"model.chkp",
                 'enable_test': nn_test, 
                 'test_episodes': test_episodes,
                 'test_episodes_len': 5000}

    Ks = [np.matrix([[-10, 0,  0, 0,  0, 0,  0],
                     [-10, 0, 10, 0,  0, 0,  0],
                     [-10, 0, 10, 0, 10, 0,  0],
                     [-10, 0, 10, 0, 10, 0, 10]])]
    mat = np.matrix(np.zeros((14, 7)))
    bias = np.matrix(np.zeros((14, 1)))
    lower = np.matrix(np.zeros((7, 1)))
    upper = np.matrix(np.zeros((7, 1)))
    for i in range(7):
        mat[2*i, i] = 1
        mat[2*i+1, i] = -1
        bias[2*i,0] = s_max[i,0]
        bias[2*i+1,0] = s_max[i,0]
        lower[i,0] = s_min[i,0]
        upper[i,0] = s_max[i,0]

    invs = [(mat, bias)]
    covers = [(mat, bias, lower, upper)]
    initial_shield = Shield(env, K_list=Ks, inv_list=invs, cover_list=covers,
            bound=episode_len)

    actor, shield = DDPG(env, args, rewardf=shield_reward,
            safe_training=safe_training,
            shields=shields, initial_shield=initial_shield)

    #################### Shield #################
    model_path = os.path.split(args['model_path'])[0]+'/'
    linear_func_model_name = 'K.model'
    model_path = model_path+linear_func_model_name+'.npy'

    def rewardf(x, Q, u, R):
        return env.reward(x, u)

    names = {0:"x0", 1:"x1", 2:"x2", 3:"x3", 4:"x4", 5:"x5", 6:"x6"}
    if shield_test:
        shield.test_shield(actor, test_episodes, 5000)

    actor.sess.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Running Options')
    parser.add_argument('--nn_test', action="store_true", dest="nn_test")
    parser.add_argument('--retrain_shield', action="store_true",
            dest="retrain_shield")
    parser.add_argument('--shield_test', action="store_true",
            dest="shield_test")
    parser.add_argument('--test_episodes', action="store",
            dest="test_episodes", type=int)
    parser.add_argument('--retrain_nn', action="store_true", dest="retrain_nn")
    parser.add_argument('--safe_training', action="store_true",
            dest="safe_training")
    parser.add_argument('--shields', action="store", dest="shields", type=int)
    parser.add_argument('--episode_len', action="store", dest="ep_len", type=int)
    parser_res = parser.parse_args()
    nn_test = parser_res.nn_test
    retrain_shield = parser_res.retrain_shield
    shield_test = parser_res.shield_test
    test_episodes = parser_res.test_episodes \
            if parser_res.test_episodes is not None else 100
    retrain_nn = parser_res.retrain_nn
    safe_training = parser_res.safe_training \
            if parser_res.safe_training is not None else False
    shields = parser_res.shields if parser_res.shields is not None else 1
    ep_len = parser_res.ep_len if parser_res.ep_len is not None else 50

    carplatoon("random_search", 200, 100, 0, [500, 400, 300],
            [600, 500, 400, 300],
            "ddpg_chkp/car-platoon/discrete/4/500400300600500400300/",
            nn_test=nn_test, retrain_shield=retrain_shield,
            shield_test=shield_test, test_episodes=test_episodes,
            retrain_nn=retrain_nn, safe_training=safe_training,
            shields=shields, episode_len=ep_len)
