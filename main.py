import numpy as np
import tensorflow as tf
import utilities
import os
from VAE2_ms_su import VAE_SU
os.environ["CUDA_VISIBLE_DEVICES"] = '0'

with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:

    Data = utilities.data()
    malware = Data.test_malicious
    benign = Data.test_benign
    data_len = malware.shape[0]

    tr_s = 'VAE2'
    KLW = 10
    NLOSSW = 10
    Def_d = VAE_SU(sess,
                   scope='musgmsu',
                   n_hidden=600,
                   dim_z=80,
                   n_epochs=20,
                   batch_size=64,
                   learn_rate=0.001,
                   Loss_type='1',
                   KLW=KLW,
                   NLOSSW=NLOSSW)

    Def_d.train_mlp(Data)

    def facc(nplabel, IsMal=True):
        if IsMal:
            return np.sum(nplabel) / nplabel.shape[0]
        else:
            return 1 - np.sum(nplabel) / nplabel.shape[0]

    def LogLoss(metricRange, filename, LkhdScale=1, KLScale=1):
        f = open(filename, 'w')
        f.close()
        for metricraw in metricRange:
            metric = float(metricraw)
            preben = Def_d.get_predict_(benign,
                                        sess,
                                        metric,
                                        lkhd_scale=LkhdScale,
                                        KL_scale=KLScale)
            premal = Def_d.get_predict_(malware,
                                        sess,
                                        metric,
                                        lkhd_scale=LkhdScale,
                                        KL_scale=KLScale)

            f = open(filename, 'a+')
            f.write('be_acc|%.6f| metric|%f|\n' %
                    (facc(preben, False), metric))
            f.write('mal_acc|%.6f| metric|%f|\n' % (facc(premal), metric))
            f.close()

    filename = 'VAE_acc.txt'
    metricList = range(0, 100, 2)
    LogLoss(metricRange=metricList, filename=filename, LkhdScale=1, KLScale=0)
