# -*- coding: utf-8 -*-
# -------------------------------
# Author: Zikang Xiong
# Email: zikangxiong@gmail.com
# Date:   2018-10-27 17:42:12
# Last Modified by:   Zikang Xiong
# Last Modified time: 2018-11-01 16:36:34
# -------------------------------
import numpy as np
from DDPG import *
from main import *
import os.path
import sys
from Environment import Environment
from shield import Shield


def carplatoon(learning_eposides, actor_structure, critic_structure, learning_method, number_of_rollouts, simulation_steps, verification_steps):
  A = np.matrix([
  [1,   0,0,   0,0, 0,0,   0,0, 0,0, 0,0, 0,0],
  [0,   1,0.1, 0,0, 0,0,   0,0, 0,0, 0,0, 0,0],
  [0,   0,1,   0,0, 0,0,   0,0, 0,0, 0,0, 0,0],
  [0,   0,0,   1,0.1, 0,0, 0,0, 0,0, 0,0, 0,0],
  [0,   0,0,   0,1,   0,0, 0,0, 0,0, 0,0, 0,0],
  [0, 0,0,   0,0,   1,0.1, 0,0, 0,0, 0,0, 0,0],
  [0, 0,0,   0,0,   0,1,   0,0, 0,0, 0,0, 0,0],
  [0, 0,0,   0,0,   0,0, 1,0.1, 0,0, 0,0, 0,0],
  [0, 0,0,   0,0,   0,0, 0,1,   0,0, 0,0, 0,0],
  [0, 0,0,   0,0,   0,0, 0,0, 1,0.1, 0,0, 0,0],
  [0, 0,0,   0,0,   0,0, 0,0, 0,1,   0,0, 0,0],
  [0, 0,0,   0,0,   0,0, 0,0, 0,0,  1,0.1,0,0],
  [0, 0,0,   0,0,   0,0, 0,0, 0,0,  0,1,  0,0],
  [0, 0,0,   0,0,   0,0, 0,0, 0,0,  0,0,1,0.1],
  [0, 0,0,   0,0,   0,0, 0,0, 0,0,  0,0,  0,1]
  ])
  B = np.matrix([
  [0.1, 0,   0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0.1, -0.1,0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0.1,-0.1, 0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0,  0.1, -0.1, 0,   0,   0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0.1,-0.1, 0,   0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0.1,-0.1, 0,   0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0,  0.1, -0.1, 0],
  [0,   0,   0,   0,   0,   0,   0,   0],
  [0,   0,   0,   0,   0,   0, 0.1,-0.1],
  ])

  #intial state space
  s_min = np.array([[ 19.9],[ 0.9], [-0.1], [ 0.9],[-0.1], [ 0.9], [-0.1], [ 0.9], [-0.1], [ 0.9],[-0.1], [ 0.9], [-0.1], [ 0.9], [-0.1]])
  s_max = np.array([[ 20.1],[ 1.1], [ 0.1], [ 1.1],[ 0.1], [ 1.1], [ 0.1], [ 1.1], [ 0.1], [ 1.1],[ 0.1], [ 1.1], [ 0.1], [ 1.1], [ 0.1]])

  #x0 =  np.matrix([[ 0.1], [-0.1], [-0.1], [-0.1], [-0.1], [-0.1], [ 0.1], [ 0.1], [-0.1], [-0.1], [-0.1], [-0.1], [ 0.1], [ 0.1], [-0.1]])
  #x0 += np.matrix([[20], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0]]) 

  Q = np.zeros((15, 15), float)
  np.fill_diagonal(Q, 1)

  R = np.zeros((8,8), float)
  np.fill_diagonal(R, .0005)

  x_min = np.array([[18],[0.5],[-1],[0.5],[-1],[0.5],[-1],[0.5],[-1],[0.5],[-1],[0.5],[-1],[0.5],[-1]])
  x_max = np.array([[22],[1.5], [1],[1.5],[ 1],[1.5],[ 1],[1.5], [1],[1.5],[ 1],[1.5],[ 1],[1.5],[ 1]])
  u_min = np.array([[-10.], [-10.], [-10.], [-10.], [-10.], [-10.], [-10.], [-10.]])
  u_max = np.array([[ 10.], [ 10.], [ 10.], [ 10.], [ 10.], [ 10.], [ 10.], [ 10.]])

  #Coordination transformation
  origin = np.array([[20], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0], [1], [0]])
  s_min -= origin
  s_max -= origin
  x_min -= origin
  x_max -= origin

  env = Environment(A, B, u_min, u_max, s_min, s_max, x_min, x_max, Q, R)

  args = { 'actor_lr': 0.0001,
           'critic_lr': 0.001,
           'actor_structure': actor_structure,
           'critic_structure': critic_structure, 
           'buffer_size': 1000000,
           'gamma': 0.99,
           'max_episode_len': 1,
           'max_episodes': learning_eposides,
           'minibatch_size': 64,
           'random_seed': 6553,
           'tau': 0.005,
           'model_path': train_dir+"model.chkp",
           'enable_test': True, 
           'test_episodes': 1,
           'test_episodes_len': 5000}
  actor = DDPG(env, args)

  #################### Shield #################
  model_path = os.path.split(args['model_path'])[0]+'/'
  linear_func_model_name = 'K.model'
  model_path = model_path+linear_func_model_name+'.npy'

  names = {0:"x0", 1:"x1", 2:"x2", 3:"x3", 4:"x4", 5:"x5", 6:"x6", 7:"x7", 8:"x8", 9:"x9", 10:"x10", 11:"x11", 12:"x12", 13:"x13", 14:"x14"}
  shield = Shield(env, actor, model_path)
  shield.train_shield(learning_method, number_of_rollouts, simulation_steps, names=names, explore_mag = 0.5, step_size = 0.5)
  shield.test_shield(1, 5000)

  ################# Metrics ######################
  actor_boundary(env, actor, 1000, 100)
  shield.shield_boundary(1000, 100)
  terminal_err = 2e-3
  sample_steps = 100
  sample_ep = 1000
  print "---\nterminal error: {}\nsample_ep: {}\nsample_steps: {}\n---".format(terminal_err, sample_ep, sample_steps)
  dist_nn_lf = metrics.distance_between_linear_function_and_neural_network(env, actor, shield.K, terminal_err, sample_ep, sample_steps)
  print "dist_nn_lf: ", dist_nn_lf
  nn_perf = metrics.neural_network_performance(env, actor, terminal_err, sample_ep, sample_steps)
  print "nn_perf", nn_perf
  shield_perf = metrics.linear_function_performance(env, shield.K, terminal_err, sample_ep, sample_steps)
  print "shield_perf", shield_perf



  actor.sess.close()

if __name__ == "__main__":
  learning_eposides = int(sys.argv[1])
  actor_structure = [int(i) for i in list(sys.argv[2].split(','))]
  critic_structure = [int(i) for i in list(sys.argv[3].split(','))]
  train_dir = sys.argv[4]
  carplatoon(learning_eposides, actor_structure, critic_structure, "random_search", 100, 200, 10) 