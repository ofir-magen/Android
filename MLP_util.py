
import tensorflow as tf
import numpy as np

class mu_sigma_MLP():
    def __init__(self,sess,num_epoch=30,batch_size=128,learn_rate=1e-3,z_dim=20):

        self.num_epoch=num_epoch
        self.batch_size=batch_size
        self.learn_rate=learn_rate

        self.sess=sess

        self.z_dim=z_dim

        self.mu_wgt=0.5
        self.sgm_wgt=0.5


    def mu_sigma_MLP_classfier(self,mu_sgm_C, n_hidden=128, n_output=2, keep_prob=1,reuse=False,var_name="mu_sgm_MLP_decoder"):

        with tf.variable_scope(var_name, reuse=reuse):

            w_init = tf.contrib.layers.variance_scaling_initializer()
            b_init = tf.constant_initializer(0.)



            w0 = tf.get_variable('w0', [mu_sgm_C.get_shape()[1], n_hidden], initializer=w_init)
            b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
            h0 = tf.matmul(mu_sgm_C, w0) + b0
            h0 = tf.nn.tanh(h0)

            h0 = tf.nn.dropout(h0, keep_prob)

            w1 = tf.get_variable('w1', [h0.get_shape()[1], n_hidden], initializer=w_init)
            b1 = tf.get_variable('b1', [n_hidden], initializer=b_init)
            h1 = tf.matmul(h0, w1) + b1
            h1 = tf.nn.elu(h1)
            h1 = tf.nn.dropout(h1, keep_prob)

            w1 = tf.get_variable('w2', [h1.get_shape()[1], n_hidden], initializer=w_init)
            b1 = tf.get_variable('b2', [n_hidden], initializer=b_init)
            h1 = tf.matmul(h0, w1) + b1
            h1 = tf.nn.elu(h1)
            h1 = tf.nn.dropout(h1, keep_prob)

            wo = tf.get_variable('wo', [h1.get_shape()[1], n_output], initializer=w_init)
            bo = tf.get_variable('bo', [n_output], initializer=b_init)
            l_3=tf.matmul(h1, wo) + bo
            l_4 = tf.sigmoid(l_3)

            self.O_LOGITS, self.O_PROBS, self.O_FEATURES = 'logits probs features'.split()
        return {self.O_LOGITS: l_3,
                    self.O_PROBS: l_4}

    def mu_sigma_MLP_classfier_one(self,mu_sgm_C, n_hidden=128, n_output=2, keep_prob=1,reuse=False,var_name="mu_sgm_MLP_decoder"):

        with tf.variable_scope(var_name, reuse=reuse):

            w_init = tf.contrib.layers.variance_scaling_initializer()
            b_init = tf.constant_initializer(0.)

            wo = tf.get_variable('wo', [mu_sgm_C.get_shape()[1], n_output], initializer=w_init)
            bo = tf.get_variable('bo', [n_output], initializer=b_init)
            l_3=tf.matmul(mu_sgm_C,wo) + bo
            l_4 = tf.sigmoid(l_3)

            self.O_LOGITS, self.O_PROBS, self.O_FEATURES = 'logits probs features'.split()
        return {self.O_LOGITS: l_3,
                    self.O_PROBS: l_4}
    def build_model(self):
        self.mu_in=tf.placeholder(dtype = tf.float32,shape = [None,self.z_dim],name = 'mu_in')
        self.sgm_in=tf.placeholder(dtype = tf.float32,shape = [None,self.z_dim],name = 'sgm_in')
        self.label_in=tf.placeholder(dtype = tf.float32,shape = [None,2],name = 'sgm_in')
        self.keep_prob = tf.placeholder(tf.float32, name='keep_prob_su_sgm')

        y1=self.mu_sigma_MLP_classfier(self.mu_in,n_hidden = 1000,keep_prob = self.keep_prob)['logits']
        y2=self.mu_sigma_MLP_classfier(self.sgm_in,n_hidden = 1000,keep_prob = self.keep_prob,
        reuse =True )['logits']

        y=self.mu_wgt*y1+self.sgm_wgt*y2

        self.loss = tf.reduce_mean(
            tf.nn.sigmoid_cross_entropy_with_logits(logits=y, labels=self.label_in))

        correct_prediction = tf.equal(tf.argmax(y,1),tf.argmax(self.label_in,1))
        self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        self.train_op= tf.train.AdamOptimizer(self.learn_rate).minimize(self.loss)

    def train(self):
        print('in train')
        self.sess.run(tf.global_variables_initializer(), feed_dict={self.keep_prob : 0.9})
        total_batch = int(self.z_num / self.batch_size)
        counter = 0
        print(total_batch)


        for epoch in range(self.num_epoch):

            for idx in range(total_batch):
                batch_mu = self.mu[idx*self.batch_size:(idx+1)*self.batch_size]
                batch_sgm=self.sgm[idx*self.batch_size:(idx+1)*self.batch_size]
                batch_label = self.label[idx * self.batch_size:(idx + 1) * self.batch_size]


                _, loss = self.sess.run([self.train_op,self.loss],
                    feed_dict={self.mu_in:batch_mu,self.sgm_in:batch_sgm,self.label_in:batch_label,self.keep_prob : 0.9})

                counter+=1

                if(counter%500==1):
                    accuracy_score = self.sess.run(self.accuracy, feed_dict={self.mu_in:batch_mu,self.sgm_in:batch_sgm,self.label_in:batch_label,self.keep_prob : 1.0})
                    print('counter',counter)
                    print("Epoch: [%2d] [%4d/%4d]  loss: %.8f"% (epoch, idx,total_batch, loss))
                    print("epoch:",epoch,"idx:",idx,"accuracy on train:%.8f"%(accuracy_score),end = '    ')
                    print("epoch:",epoch,"idx:",idx,"accuracy on test_:%.8f"%(self.test()))


    def test(self):
        accuracy_score = self.sess.run(self.accuracy, feed_dict={self.mu_in:self.test_mu,self.sgm_in:self.test_sgm,self.label_in:self.test_label,self.keep_prob : 1.0})
        return accuracy_score
