import tensorflow as tf
import numpy as np
import VAE_util
import MLP_util
from cleverhans.model import Model
from utilities import get_label, softmax


class VAE_SU(Model):
    def __init__(self, sess,scope,
        n_hidden,dim_z,n_epochs,batch_size ,
        learn_rate,Loss_type,KLW=10,NLOSSW=10, **kwargs):
        del kwargs

        self.scope = scope
        self.nb_classes = 2
        self.hparams =locals()

        self.sess=sess

        self.Mlp=MLP_util.mu_sigma_MLP(self.sess,
                num_epoch=n_epochs,
                batch_size=batch_size,learn_rate=learn_rate,
                z_dim = dim_z)
        self.Mlp.build_model()

        self.Vae=VAE_util.VAE_2(self.sess,results_path='results_t',dim_z=dim_z,add_noise=False,
                 n_hidden=n_hidden,learn_rate=1e-3,num_epochs=50,batch_size=128,
                 save_ms=True,save_decode=True,loss_type=Loss_type,KLW=KLW,NLOSSW=NLOSSW, dim_feature=379)
        self.Vae.build_model()
        self.dim=self.Vae.dim_img
    def fprop(self,a=None,**kwargs):
        mu=self.Vae.mu
        sgm=self.Vae.sigma
        mu_sgm=tf.concat((mu,sgm),axis = 1)

        y=self.Mlp.mu_sigma_MLP_classfier(mu_sgm,n_hidden = 40,
                keep_prob = self.Mlp.keep_prob,reuse = tf.AUTO_REUSE,
                var_name = 'main_mu_frop')['logits']

        self.O_LOGITS, self.O_PROBS, self.O_FEATURES = 'logits probs features'.split()
        return {self.O_LOGITS: y,
                    self.O_PROBS: tf.sigmoid(y)}


    def train_mlp(self, Data):
        test_ben=Data.test_benign
        test_mal=Data.test_malicious
        test_ben_label=get_label(test_ben.shape[0], True)
        test_mal_label=get_label(test_mal.shape[0], False)
        y=self.fprop()['logits']
        t_vars = tf.trainable_variables()

        mu_vars = [var for var in t_vars if 'main_mu_frop' in var.name]
        sgm_vars = [var for var in t_vars if 'main_sgm_frop' in var.name]

        loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=y,
                                labels=self.Vae.label_x))
        self.y=y
        correct_prediction = tf.equal(tf.argmax(y,1),tf.argmax(self.Vae.label_x,1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
        self.accuracy=accuracy
        self.sess.run(tf.variables_initializer(mu_vars+sgm_vars), feed_dict={self.Mlp.keep_prob : 0.9,self.Vae.keep_prob : 0.9})
        train_op= tf.train.AdamOptimizer(self.Mlp.learn_rate).minimize(loss,var_list = mu_vars+sgm_vars)


        self.Vae.train(Data)
        total_batch = int(self.Vae.n_samples / self.Mlp.batch_size)
        counter = 0
        print('will in for')
        for epoch in range(self.Mlp.num_epoch):

            np.random.shuffle(self.Vae.mal_data)
            np.random.shuffle(self.Vae.ben_data)
            lbBen=get_label(self.Mlp.batch_size,True)
            lbMal=get_label(self.Mlp.batch_size,False)
            batch_label=np.row_stack((lbBen,lbMal))
            for idx in range(total_batch):
                offset = (idx *self.Mlp.batch_size) % (self.Vae.n_samples)
                batch_ben_input = self.Vae.ben_data[offset:(offset + self.Mlp.batch_size), :]
                batch_mal_input = self.Vae.mal_data[offset:(offset + self.Mlp.batch_size), :]

                batch_xs_input = np.row_stack((batch_ben_input,batch_mal_input))
                batch_xs_label = batch_label

                _, rloss = self.sess.run([train_op,loss],
                feed_dict={self.Vae.x:batch_xs_input,
                           self.Vae.label_x:batch_xs_label,
                           self.Vae.keep_prob : 1.0,self.Mlp.keep_prob : 0.9})

                counter+=1

                if(counter%500==1):
                    accuracy_score = self.sess.run(accuracy, feed_dict={self.Vae.x: batch_xs_input,self.Vae.label_x:batch_xs_label,self.Vae.keep_prob : 1.0,self.Mlp.keep_prob : 1.0})
                    print('counter',counter)
                    print("Epoch: [%2d] [%4d/%4d]  loss: %.8f"% (epoch, idx,total_batch, rloss))
                    print("epoch:",epoch,"idx:",idx,"accuracy on train:%.8f"%(accuracy_score),end = '    ')
                    test_acc_ben=self.test_(self.sess, accuracy, self.Vae.x, self.Vae.label_x, self.Vae.keep_prob, self.Mlp.keep_prob, test_ben, test_ben_label)
                    print("epoch:",epoch,"idx:",idx,"accuracy on ben:%.8f"%(test_acc_ben))
                    test_acc_mal=self.test_(self.sess, accuracy, self.Vae.x, self.Vae.label_x, self.Vae.keep_prob, self.Mlp.keep_prob, test_mal, test_mal_label)
                    print("epoch:",epoch,"idx:",idx,"accuracy on mal:%.8f"%(test_acc_mal))


    def test_(self, sess, acc, pb_x, pb_l, pb_k, pb_k2, test_data, test_label):
        accuracy_score = sess.run(acc, feed_dict={pb_x: test_data,pb_l:test_label,pb_k : 1.0,pb_k2 : 1.0})
        return accuracy_score


    def get_reloss_(self,sess,data):
        all_reloss=sess.run(self.Vae.neg_marginal_likelihood+self.Vae.KL_divergence,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        kl_reloss=sess.run(self.Vae.KL_divergence,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        likehood_reloss=sess.run(self.Vae.neg_marginal_likelihood,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})

        return all_reloss,kl_reloss,likehood_reloss


    def get_eve_reloss_(self,sess,data,lkhd_scale=1,KL_scale=1):
        reloss=sess.run(lkhd_scale*self.Vae.or_neg_marginal_likelihood+
                        KL_scale*self.Vae.or_KL_divergence,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})

        return reloss


    def save_eve_reloss_(self,sess,data,savename,lkhd_scale=1,KL_scale=1):
        reloss=self.get_eve_reloss_(sess,data,lkhd_scale,KL_scale)
        np.save(savename+'.npy',reloss)
        likehood=sess.run(self.Vae.or_neg_marginal_likelihood,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        KL=sess.run(self.Vae.or_KL_divergence,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        np.save(savename+'_lik.npy',likehood)
        np.save(savename+'_KL.npy',KL)


    def print_eve_reloss_(self,sess,data,save,savename):

        likehood=sess.run(self.Vae.or_neg_marginal_likelihood,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        KL=sess.run(self.Vae.or_KL_divergence,feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0})
        print('likehood',likehood)
        print('KL',KL)
        if save :
            np.save(savename+'_lik.npy',likehood)
            np.save(savename+'_KL.npy',KL)


    def get_predict_(self,data,sess=None,metric=200,lkhd_scale=1,KL_scale=0,SaveName=None):
        if sess==None:
            sess=self.sess
        data=np.reshape(data,(-1,self.dim)).astype(np.float32)
        label=sess.run(tf.argmax(self.y,axis = 1,name='get_predict'),
                    feed_dict={self.Vae.x:data,self.Vae.keep_prob:1.0,
                    self.Mlp.keep_prob:1.0})
        label=np.reshape(label,(1,-1))

        reloss=self.get_eve_reloss_(sess,data=data,lkhd_scale=lkhd_scale,KL_scale=KL_scale).reshape(label.shape)
        if SaveName==None:
            pass

        elif SaveName!=None:
            np.save(SaveName+'MLP.npy',label)
            OneReloss=np.zeros_like(label)
            for i in range(reloss.shape[1]):
                if reloss[0][i]>metric:
                    OneReloss[0][i]=1
            np.save(SaveName+'FDVAE.npy',OneReloss)

        for  i in range(reloss.shape[1]):
            if reloss[0][i]>metric:
                label[0][i]=1

        if SaveName!=None:
            np.save(SaveName+'Final.npy',label)
        return np.reshape(label,(-1,1))

        if SaveName!=None:
            np.save(SaveName+'Final.npy',label)
        return np.reshape(label,(-1,1))
