
import tensorflow as tf
import numpy as np
from utilities import get_label


class VAE_2():
    pass
    def __init__(self,sess,results_path='results',dim_z=20,add_noise=False,
                 n_hidden=200,learn_rate=1e-3,num_epochs=50,batch_size=128,
                 save_ms=True,save_decode=True,loss_type='1',KLW=5,NLOSSW=10, dim_feature=379):
        self.sess=sess

        self.RESULTS_DIR =results_path

        self.ADD_NOISE =add_noise

        self.n_hidden = n_hidden


        self.dim_z = dim_z


        self.n_epochs = num_epochs
        self.batch_size = batch_size
        self.learn_rate = learn_rate


        self.Save_ms=save_ms
        self.Save_decode=save_decode
        self.dim_img = dim_feature


        self.loss_type=loss_type
        self.KLW=KLW
        self.NLOSSW=NLOSSW
        self.SaveLossFilename='SavelossKLW%d_NLW%d_'%(self.KLW,self.NLOSSW)+loss_type+'.txt'
        print('*'*3,self.KLW,' '*3,self.NLOSSW)


    def build_model(self):
        in_build =True
        self.x_hat = tf.placeholder(tf.float32, shape=[None, self.dim_img], name='input_img')
        self.x = tf.placeholder(tf.float32, shape=[None, self.dim_img], name='target_img')
        self.x_comp = tf.placeholder(tf.float32, shape=[None, self.dim_img], name='improve_img')
        self.label_x = tf.placeholder(tf.float32, shape=[None, 2], name='label_img')
        self.label_x_comp = tf.placeholder(tf.float32, shape=[None, 2], name='label_imgcom')

        self.keep_prob = tf.placeholder(tf.float32, name='keep_prob_vae2')

        self.z_in = tf.placeholder(tf.float32, shape=[None, self.dim_z], name='latent_variable')
        self.labelindex=tf.placeholder(tf.int32,shape=(128,))


        mu, sigma = self.gaussian_MLP_encoder(self.x_hat, self.n_hidden, self.dim_z, self.keep_prob)
        mu1, sigma1 = self.gaussian_MLP_encoder(self.x_comp, self.n_hidden,self.dim_z, self.keep_prob)
        muvae, sigmavae = self.gaussian_MLP_encoder(self.x, self.n_hidden, self.dim_z, self.keep_prob)

        self.mu=muvae
        self.sigma=sigmavae


        z = self.mu + self.sigma * tf.random_normal(tf.shape(self.mu), 0, 1, dtype=tf.float32)
        y = self.bernoulli_MLP_decoder(z, self.n_hidden, self.dim_img, self.keep_prob)
        y = tf.clip_by_value(y, 1e-8, 1 - 1e-8)

        marginal_likelihood = tf.reduce_sum(self.x * tf.log(y+1e-8) + (1 - self.x) * tf.log(1 - y+1e-8), 1)
        KL_divergence = 0.5 * tf.reduce_sum(tf.square(self.mu) + tf.square(self.sigma) - tf.log(1e-8 + tf.square(self.sigma)) - 1, 1)

        vector_loss = tf.reduce_mean(tf.square(self.label_x_comp-self.label_x), 1)
        loss_bac = 60*vector_loss
        loss_mean = tf.reduce_mean(tf.square(mu-mu1),1)


        loss_0 =tf.reduce_mean(tf.multiply(loss_mean,1-vector_loss))
        loss_1 =tf.reduce_mean(tf.multiply(tf.abs(tf.nn.relu(loss_bac-loss_mean)),vector_loss))


        self.or_neg_marginal_likelihood=-marginal_likelihood
        self.or_KL_divergence=KL_divergence
        marginal_likelihood = tf.reduce_mean(marginal_likelihood)
        KL_divergence = tf.reduce_mean(KL_divergence)
        ELBO = self.KLW*marginal_likelihood - KL_divergence

        loss = -ELBO

        self.y=y
        self.z=z
        self.loss=loss
        self.neg_marginal_likelihood=-marginal_likelihood
        self.KL_divergence=KL_divergence
        self.new_loss=(loss_1+loss_0)*self.NLOSSW


        add_new_loss=self.loss
        print("self.loss_type",self.loss_type)
        if self.loss_type[0]=='1':
            add_new_loss=add_new_loss+self.new_loss


        self.newtrain_op = tf.train.AdamOptimizer(self.learn_rate).minimize(add_new_loss)


        in_build=False
    def train(self, Data):
        self.ben_data=Data.train_benign
        self.mal_data=np.row_stack((Data.train_malicious,Data.train_malicious))
        self.n_samples=min(self.mal_data.shape[0],self.ben_data.shape[0])

        total_batch = int(self.n_samples / self.batch_size)
        counter=0
        self.sess.run(tf.global_variables_initializer(), feed_dict={self.keep_prob : 0.9})
        f=open(self.SaveLossFilename,'a+')
        for epoch in range(self.n_epochs):
            np.random.shuffle(self.mal_data)
            np.random.shuffle(self.ben_data)
            lbBen=get_label(self.batch_size,True)
            lbMal=get_label(self.batch_size,False)
            batch_label=np.row_stack((lbBen,lbMal))


            for i in range(total_batch):

                offset = (i * self.batch_size) % (self.n_samples)
                batch_ben_input_s = self.ben_data[offset:(offset + self.batch_size), :]
                batch_mal_input_s = self.mal_data[offset:(offset + self.batch_size), :]
                batch_input=np.row_stack((batch_ben_input_s,batch_mal_input_s))
                batch_input_wl=np.column_stack((batch_input,batch_label))
                np.random.shuffle(batch_input_wl)


                batch_xs_input = batch_input_wl[:,:-2]
                batch_xs_label = batch_input_wl[:,-2:]
                offset = ((i+1) * self.batch_size) % (self.n_samples-self.batch_size)

                batch_ben_input_s = self.ben_data[offset:(offset + self.batch_size), :]
                batch_mal_input_s = self.mal_data[offset:(offset + self.batch_size), :]
                batch_input=np.row_stack((batch_ben_input_s,batch_mal_input_s))
                batch_input_wl=np.column_stack((batch_input,batch_label))
                np.random.shuffle(batch_input_wl)

                batch_xcomp_input = batch_input_wl[:,:-2]
                batch_xcomp_label = batch_input_wl[:,-2:]

                batch_xs_target = self.ben_data[offset:(offset + self.batch_size), :]
                batch_xs_target=np.row_stack((batch_xs_target,batch_xs_target))
                assert batch_xs_input.shape==batch_xs_target.shape


                _, tot_loss, loss_likelihood, loss_divergence,newloss = \
                    self.sess.run((self.newtrain_op,
                    self.loss, self.neg_marginal_likelihood,
                    self.KL_divergence,self.new_loss)
                    ,feed_dict={self.x_hat: batch_xs_input, self.x: batch_xs_target,
                               self.keep_prob : 0.9,self.label_x:batch_xs_label,
                               self.label_x_comp:batch_xcomp_label, self.x_comp: batch_xcomp_input})

                f.write('|%d| likehoodloss|%.6f|KL|%.6f|newloss|%.6f|'%(counter,loss_likelihood, loss_divergence,newloss)+'\n')
                counter=counter+1

            print("epoch[ %d/%d]: L_tot %03.2f L_likelihood %03.2f L_divergence %03.2f " % (epoch,self.n_epochs, tot_loss, loss_likelihood, loss_divergence))
        f.close()

    def gaussian_MLP_encoder(self,x, n_hidden, n_output, keep_prob):
        with tf.variable_scope("gaussian_MLP_encoder",reuse=tf.AUTO_REUSE):

            w_init = tf.contrib.layers.variance_scaling_initializer()
            b_init = tf.constant_initializer(0.)


            w0 = tf.get_variable('w0', [x.get_shape()[1], n_hidden], initializer=w_init)
            b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
            h0 = tf.matmul(x, w0) + b0
            h0 = tf.nn.elu(h0)
            h0 = tf.nn.dropout(h0, keep_prob)


            w1 = tf.get_variable('w1', [h0.get_shape()[1], n_hidden], initializer=w_init)
            b1 = tf.get_variable('b1', [n_hidden], initializer=b_init)
            h1 = tf.matmul(h0, w1) + b1
            h1 = tf.nn.tanh(h1)
            h1 = tf.nn.dropout(h1, keep_prob)


            wo = tf.get_variable('wo', [h1.get_shape()[1], n_output * 2], initializer=w_init)
            bo = tf.get_variable('bo', [n_output * 2], initializer=b_init)
            gaussian_params = tf.matmul(h1, wo) + bo


            mean = gaussian_params[:, :n_output]

            stddev = 1e-6 + tf.nn.softplus(gaussian_params[:, n_output:])

        return mean, stddev


    def bernoulli_MLP_decoder(self,z, n_hidden, n_output, keep_prob, reuse=False):

        with tf.variable_scope("VAE_bernoulli_MLP_decoder", reuse=reuse):

            w_init = tf.contrib.layers.variance_scaling_initializer()
            b_init = tf.constant_initializer(0.)


            w0 = tf.get_variable('w0', [z.get_shape()[1], n_hidden], initializer=w_init)
            b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
            h0 = tf.matmul(z, w0) + b0
            h0 = tf.nn.tanh(h0)
            h0 = tf.nn.dropout(h0, keep_prob)


            w1 = tf.get_variable('w1', [h0.get_shape()[1], n_hidden], initializer=w_init)
            b1 = tf.get_variable('b1', [n_hidden], initializer=b_init)
            h1 = tf.matmul(h0, w1) + b1
            h1 = tf.nn.elu(h1)
            h1 = tf.nn.dropout(h1, keep_prob)


            wo = tf.get_variable('wo', [h1.get_shape()[1], n_output], initializer=w_init)
            bo = tf.get_variable('bo', [n_output], initializer=b_init)
            y = tf.sigmoid(tf.matmul(h1, wo) + bo)

        return y
    def bernoulli_MLP_decoder_B(self,z, n_hidden, n_output, keep_prob, reuse=False):

        with tf.variable_scope("bernoulli_MLP_decoder", reuse=reuse):

            w_init = tf.contrib.layers.variance_scaling_initializer()
            b_init = tf.constant_initializer(0.)


            w0 = tf.get_variable('w0', [z.get_shape()[1], n_hidden], initializer=w_init)
            b0 = tf.get_variable('b0', [n_hidden], initializer=b_init)
            h0 = tf.matmul(z, w0) + b0
            h0 = tf.nn.tanh(h0)
            h0 = tf.nn.dropout(h0, keep_prob)


            w1 = tf.get_variable('w1', [h0.get_shape()[1], n_hidden], initializer=w_init)
            b1 = tf.get_variable('b1', [n_hidden], initializer=b_init)
            h1 = tf.matmul(h0, w1) + b1
            h1 = tf.nn.elu(h1)
            h1 = tf.nn.dropout(h1, keep_prob)


            wo = tf.get_variable('wo', [h1.get_shape()[1], n_output], initializer=w_init)
            bo = tf.get_variable('bo', [n_output], initializer=b_init)
            y = tf.sigmoid(tf.matmul(h1, wo) + bo)

        return y
    def decoder(self,z, dim_img, n_hidden):
        y = self.bernoulli_MLP_decoder(z, n_hidden, dim_img, 1.0, reuse=True)
        return y
