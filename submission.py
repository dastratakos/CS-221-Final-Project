'''
File: submission.py
----------
This file contains our implementations of value iteration and Q-learning.
'''

import util, math, random, csv, timeit
from collections import defaultdict
from util import ValueIteration
from itertools import combinations

class RacquetsMDP(util.MDP):
    def __init__(self, numRacquets, file, numDays, returnProb):
        """
        numRacquets: number of racquets that can be string in a day
        numDays: number of days to consider
        data: tuple of racquet job request data
        returnProb: probability that a customer is unsatisfied with job
        """
        self.numRacquets = numRacquets
        self.data = self.readFile(file)
        self.numDays = min(numDays, len(self.data))
        self.returnProb = returnProb
        # TODO: add variable for costs of stringing racquets

    # file is a string that is the name of the CSV data file
    # returns a data structure of racquets with their data, grouped by day
    # data structure is a tuple of lists; each list represents one day of
    #   racquet intakes as a list of tuples; each tuple is a racquet
    def readFile(self, file):
        f = open(file, 'r') # to read the file
        fileReader = csv.reader(f)
        data = []
        day = []
        currDate = 0
        for lineNum, row in enumerate(fileReader):
            daysUntilDue = (1*(row[2] == 'Exp')) + (3*(row[2] == 'Std'))
            reqType = row[2]                        # to build request string
            if row[1] == 'TRUE': reqType += 'SMT'   # to build request string
            else: reqType += 'Reg'                  # to build request string
            if lineNum == 0:
                continue
            elif lineNum == 1:
                day.append((reqType, daysUntilDue))
                currDate = row[3]
            else:
                if row[3] == currDate:
                    day.append((reqType, daysUntilDue))
                else:
                    data.append(day)
                    day = []
                    day.append((reqType, daysUntilDue))
                    currDate = row[3]
        data.append(day)
#        return tuple(data)
        print('=' * 36, ' data  ', '=' * 37)
        for n, d in enumerate(data): print(n, ' : ', d)
        return data

    # Start state is an empty list of racquets at the start of Day 0
    def startState(self):
        # return ((), 0)
        return ((tuple(self.data[0]), 1))

    '''
    NOTE: might need to check for empty list of racquets
    '''
    # Return a list of lists representing actions possible from |state|.
    # One action is a list of racquets that represent picking any self.numRacquets (or fewer) racquets.
    def actions(self, state):
        if state == (): return [0]
        if len(state[0]) < self.numRacquets: # all racquets can be strung for that day
            return [state[0]] # return list of all racquets
        # otherwise, there are more racquets to string that can be strung for that day
        return set(combinations(state[0], self.numRacquets))

    # TODO: add a count of number of racquets rejected, then compute probability of that happening
    # Given a |state| and |action|, returns a list of (newState, prob, reward) tuples
    # corresponding to the states reachable from |state| when taking |action|.
    # If |state| is an end state, returns an empty list [].
    def succAndProbReward(self, state, action):
        # end state when we reach the end of the window of days
        if state[1] == self.numDays + 1: return []
        
        racquets = list(state[0])
        strung = []
        
        # TODO: (add in probability of customer unsatisfied -> transition probabilities)
        for racquet in action:
            strung.append(racquet)
        
        # remove racquets based on the action and compute reward of stringing those racquets
        for racquet in strung:
            racquets.remove(racquet)
        
        # decrement days until due for remaining racquets
        for i in range(len(racquets)):
            racquet = racquets[i]
            racquets[i] = (racquet[0], racquet[1] -  1)
        
        # add new racquets for next day
        # (generate new data -> transition probabilities?)
#        racquets += self.data[state[1]]
        if state[1] <= len(self.data) - 1:
            for racquet in self.data[state[1]]:
                if len(racquets) >= self.numRacquets + 5: break ### COMMENT IN/OUT TO SEE DIFFERENCE IN RUN TIME (this sets upper bound on having too many requests built up)
                racquets.append(racquet)
        racquets.sort(key = lambda x: x[0]+str(x[1]))        
            
        # compute reward in $, $20 penalty if racquet will be overdue, $10 penalty if racquet will be overdue in following day
        #if requests are same type, then break the tie by assigning slightly higher reward for stringing the older one
        reward = 0
        for racquet in strung:
            if racquet[0] == 'SpdReg':
                reward += 40
            elif racquet[0] == 'ExpReg':
                reward += (30 + (1 - racquet[1])*.01)
            elif racquet[0] == 'StdReg':
                reward += (20 + (3 - racquet[1])*.01)
            elif racquet[0] == 'SpdSMT':
                reward += 18
                #reward += 32
            elif racquet[0] == 'ExpSMT':
                reward += (18 + (1 - racquet[1])*.01)
                #reward += (22 + (1 - racquet[1])*.01)
            elif racquet[0] == 'StdSMT':
                reward += (18 + (3 - racquet[1])*.01)
            #look at the unstrung racquets and penalize if they are overdue
            for i in range(len(racquets)):
                unstrung = racquets[i]
                if (unstrung[1] < 0): reward += (20 * unstrung[1])
                if (unstrung[1] - 1 < 0): reward += (10 * unstrung[1] - 1)
            #print("racquet: ", racquet, " ", reward)
            
        return [((tuple(racquets), state[1] + 1), 1, reward)]

    # Set the discount factor (float or integer).
    def discount(self):
        return 1

# '''
#############################################################################################################################

# Performs Q-learning.  Read util.RLAlgorithm for more information.
# actions: a function that takes a state and returns a list of actions.
# discount: a number between 0 and 1, which determines the discount factor
# featureExtractor: a function that takes a state and action and returns a list of (feature name, feature value) pairs.
# explorationProb: the epsilon value indicating how frequently the policy
# returns a random action
class QLearningAlgorithm(util.RLAlgorithm):
    def __init__(self, actions, discount, featureExtractor, explorationProb=0.2):
        self.actions = actions
        self.discount = discount
        self.featureExtractor = featureExtractor
        self.explorationProb = explorationProb
        self.weights = defaultdict(float)
        self.numIters = 0
        self.qStarActions = defaultdict(list)

    # Return the Q function associated with the weights and features
    def getQ(self, state, action):
        score = 0.0
        f, v = self.featureExtractor(state, action)
        score += self.weights[tuple(f)] * v
        return score

    # Sets QStar to a policy (after running simulation)
    def setQStar(self, policy):
        self.qStarActions = policy

    # # Returns an action from QStar[state]
    # def getQStarAction(self, state):
    #     if self.qStarActions[state] == []: return None
    #     return self.qStarActions[state][0]

    # This algorithm will produce an action given a state.
    # Here we use the epsilon-greedy algorithm: with probability
    # |explorationProb|, take a random action.
    def getAction(self, state):
        self.numIters += 1
        if random.random() < self.explorationProb:
            return random.choice(list(self.actions(state)))
        else:
            return max((self.getQ(state, action), action) for action in self.actions(state))[1]

    # Call this function to get the step size to update the weights.
    def getStepSize(self):
        return 1.0 / math.sqrt(self.numIters)

    # We will call this function with (s, a, r, s'), which you should use to update |weights|.
    # Note that if s is a terminal state, then s' will be None.  Remember to check for this.
    # You should update the weights using self.getStepSize(); use
    # self.getQ() to compute the current estimate of the parameters.
    def incorporateFeedback(self, state, action, reward, newState):
        # BEGIN_YOUR_CODE (our solution is 9 lines of code, but don't worry if you deviate from this)
        target = reward
        if newState is not None:
            qOpt = [self.getQ(newState, action) for action in self.actions(newState)]
            target += self.discount * max(qOpt)
        prediction = self.getQ(state, action)
        name, value = self.featureExtractor(state, action)
        self.weights[name] -= self.getStepSize() * (prediction - target) * value
        # END_YOUR_CODE

# Return a single-element list containing a binary (indicator) feature
# for the existence of the (state, action) pair.  Provides no generalization.
def identityFeatureExtractor(state, action):
    # print(state[0])
    featureKey = (tuple(state[0]), action)
    featureValue = 1
    return featureKey, featureValue

'''
############################################################
# Reference Blackjack Problem 4b: convergence of Q-learning
# Small test case
# smallMDP = BlackjackMDP(cardValues=[1, 5], multiplicity=2, threshold=10, peekCost=1)
smallMDP = RacquetsMDP()

# Large test case
#largeMDP = BlackjackMDP(cardValues=[1, 3, 5, 8, 10], multiplicity=3, threshold=40, peekCost=1)
largeMDP = RacquetsMDP()
'''
def simulate_QL_over_MDP(mdp, featureExtractor):
    # Q-learning
    mdp.computeStates()
    qLearn = QLearningAlgorithm(mdp.actions, mdp.discount(), featureExtractor)
    r, qStar = util.simulate(mdp, qLearn, 1000)
    qLearn.setQStar(qStar)
    # for line in qLearn.qStarAction:
    #     print(line, ':', qLearn.qStarAction[line])
    valueIter = ValueIteration()
    valueIter.solve(mdp)
    
    qLearn.explorationProb = 0

    # compare
    diff = 0.0
    for state in valueIter.pi:
        if qLearn.qStarActions[state] != [] and valueIter.pi[state] != qLearn.qStarActions[state][0]:
            diff += 1
        elif qLearn.qStarActions[state] != [] and valueIter.pi[state] == qLearn.qStarActions[state][0]:
            print('Same policy mapping \n\t STATE---', state, '\n\t\t--- to action ---', valueIter.pi[state])
    print('Number of different policy instructions: ', diff)
    print('Length of pi_valueIter: ', len(valueIter.pi))
    print('Length of pi_QStar: ', len(qLearn.qStarActions))
    print('Difference over length of pi_valueIter:', diff / len(valueIter.pi))
    print('Difference over length of pi_QStar:', diff / len(qLearn.qStarActions))
    # END_YOUR_CODE
# '''

        
def testMDP():
    print('$'*400)
    mdp = RacquetsMDP(4, 'test_data_save.csv', 6, 0.10)
    algorithm = ValueIteration() # implemented for us in util.py
    algorithm.solve(mdp, .001)
    print('*' * 60)
    # states = sorted(algorithm.pi, key=lambda x: x[1]) # sort by day
    states = sorted(algorithm.pi, key=lambda x: len(x)) # sorted by state space
    for state in states:
        print('state:', state)
        print('\toptimal action:', algorithm.pi[state])
    # for item in list(algorithm.V): print(item, '--------', algorithm.V[item])
    # '''
    qLearn = QLearningAlgorithm(mdp.actions, mdp.discount(), identityFeatureExtractor)
    rewards, policyMap = util.simulate(mdp, qLearn, 1000)
    for state in policyMap.keys():
        print('*'*100)
        print('If you are in this state: ', state)
        print('    Policy is to take this action: ', policyMap[state][0])
        print('        Expected reward: ', policyMap[state][1])
    print('='*30, 'We have -', len(policyMap.keys()), '- total state:policy pairs', '='*30)
    # for n, reward in enumerate(rewards):
    #     print(n, '===', reward)
    # print(max(rewards))
    # '''


# # Testing what happens when learning a policy
# def learnPolicy():
#     print('='*40, 'Learning a policy', '='*40)
#     mdp = RacquetsMDP(13, 'training_data_small.csv', 10, 0)       # This tests "training" over a large state space
#     # mdp = RacquetsMDP(15, 'training_data.csv', 10, 0)     # Tests training over a smaller state space since can do more racquets per day
#     algorithm = ValueIteration() # implemented for us in util.py
#     algorithm.solve(mdp, .001)
#     print('*' * 60)
#     return algorithm.pi, algorithm.V

# testMDP()
start = timeit.default_timer()

# mdp = RacquetsMDP(4, 'test_data_save.csv', 6, 0.10)
mdp = RacquetsMDP(13, 'training_data_small.csv', 7, 0.10)
# mdp.computeStates()
# qLearn = QLearningAlgorithm(mdp.actions, mdp.discount(), identityFeatureExtractor)
# rewards, policyMap = util.simulate(mdp, qLearn, 1000)
# qLearn.qStarAction = policyMap
# for state in policyMap.keys():
#     print('*'*100)
#     print('If you are in this state: ', state)
#     print('    Policy is to take this action: ', policyMap[state][0])
#     print('        Expected reward: ', policyMap[state][1])
# print('='*30, 'Our Q* policy has -', len(policyMap.keys()), '- total state:action pairs', '='*30)
# sortedRewards = sorted(rewards)
# print(len(rewards))
# for i in range(100):
#     print(-(i + 1) * 10, sortedRewards[-(i + 1) * 10])
simulate_QL_over_MDP(mdp, identityFeatureExtractor)



# Below is simple code to test whether a policy can be learned over a large amount of test data
# pOpt, vOpt = learnPolicy()
### Uncomment below to see outputs ###
# for state in pOpt.keys():
#     print('-'*15, 'describing a policy', '-'*15)
#     print('State: ', state)
#     print('    Optimal action: ', pOpt[state])
#     print('='*100)

# for key in vOpt.keys():
#     print('Optimal value given state: ', key)
#     print('    = ', vOpt[key])
#     print()

# bestKey = max(vOpt, key=lambda x: vOpt[x])
# print('Optimal Value === ', vOpt[bestKey], '=== Found from state: ', bestKey)

