import numpy as np
def get_label(length,IsBenign):
    '''
    Get label. 
    length: the number of labels.
    IsBen: Whether the required labels are benign.
    '''
    assert length-int(length)<0.01
    length=int(length)
    ones=np.ones((length,1))
    zeros=np.zeros((length,1))
    if IsBenign:
        return np.column_stack((ones,zeros))
    else :
        return np.column_stack((zeros,ones))

def softmax(x, axis=1):
    '''
    softmax
    '''
    row_max = x.max(axis=axis)
    row_max=row_max.reshape(-1, 1)
    x = x - row_max
    x_exp = np.exp(x)
    x_sum = np.sum(x_exp, axis=axis, keepdims=True)
    s = x_exp / x_sum
    return s

class data():
    def __init__(self,test_length=1500,shuffle_=False):
        self.all_malicious=np.load('malicious.npy')[:,:-2]
        self.all_benign=np.load('benign.npy')[:,:-2]
        if shuffle_:
            np.random.shuffle(self.all_malicious)
            np.random.shuffle(self.all_benign)
        self.train_malicious=self.all_malicious[:-test_length]
        self.test_malicious=self.all_malicious[-test_length:]
        self.train_benign=self.all_benign[:-test_length]
        self.test_benign=self.all_benign[-test_length:]