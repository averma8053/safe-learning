import sys
sys.path.append(".")

from main import *
from Environment import Environment
from shield import Shield
from DDPG import *
import argparse

def quadcopter (learning_method, number_of_rollouts, simulation_steps,
        learning_eposides, actor_structure, critic_structure, train_dir,
        nn_test=False, retrain_shield=False, shield_test=False,
        test_episodes=100, retrain_nn=False, safe_training=False, shields=1,
        episode_len=100):

    A = np.matrix([[1,1], [0,1]])
    B = np.matrix([[0],[1]])

    #intial state space
    s_min = np.array([[-0.5],[-0.5]])
    s_max = np.array([[ 0.5],[ 0.5]])

    # LQR quadratic cost per state
    Q = np.matrix("1 0; 0 0")
    R = np.matrix("1.0")

    x_min = np.array([[-1.],[-1.]])
    x_max = np.array([[ 1.],[ 1.]])
    u_min = np.array([[-15.]])
    u_max = np.array([[ 15.]])

    env = Environment(A, B, u_min, u_max, s_min, s_max, x_min, x_max, Q, R)

    x_mid = (x_min + x_max) / 2.0
    def safety_reward(x, Q, u, R):
        return -np.matrix([[np.sum(np.abs(x - x_mid))]])

    if retrain_nn:
        args = { 'actor_lr': 0.001,
               'critic_lr': 0.01,
               'actor_structure': actor_structure,
               'critic_structure': critic_structure, 
               'buffer_size': 1000000,
               'gamma': 0.99,
               'max_episode_len': episode_len,
               'max_episodes': 5000,    # originally 1000
               'minibatch_size': 64,
               'random_seed': 6553,
               'tau': 0.005,
               'model_path': train_dir+"retrained_model.chkp",
               'enable_test': nn_test, 
               'test_episodes': test_episodes,
               'test_episodes_len': 5000}
    else:
        args = { 'actor_lr': 0.001,
               'critic_lr': 0.01,
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

    Ks = [np.matrix([[-2, -1]])]
    invs = [(np.matrix([[1, 0], [-1, 0], [0, 1], [0, -1]]),
        np.matrix([[0.5], [0.5], [0.5], [0.5]]))]
    covers = [(invs[0][0], invs[0][1],
        np.matrix([[-0.5], [-0.5]]),
        np.matrix([[0.5], [0.5]]))]

    initial_shield = Shield(env, K_list=Ks, inv_list=invs, cover_list=covers,
            bound=episode_len)

    actor, shield = DDPG(env, args=args, rewardf=safety_reward,
            safe_training=safe_training, shields=shields,
            initial_shield=initial_shield)

    ################# Shield ######################
    model_path = os.path.split(args['model_path'])[0]+'/'
    linear_func_model_name = 'K.model'
    model_path = model_path+linear_func_model_name+'.npy'

    if shield_test:
        shield.test_shield(actor, test_episodes, 5000, mode="single")

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

    quadcopter("random_search", 50, 100, 0, [240,200], [280,240,200],
            "ddpg_chkp/quadcopter/240200280240200/", nn_test=nn_test,
            retrain_shield=retrain_shield, shield_test=shield_test,
            test_episodes=test_episodes, retrain_nn=retrain_nn,
            safe_training=safe_training, shields=shields, episode_len=ep_len)
