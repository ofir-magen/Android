# Robust-Android-Malware-Detection-Against-Adversarial-Example-Attacks




## Features Used in This Paper
This paper uses a total of 379 features collected from .apk file.
There are 126 action features, 106 API features and 147 permission features and these features are shown in `list_total_actions.txt`, `list_total_apis.txt` and `list_total_permissions.txt` respectively.

The code & tools in `feature_extract` can be used to extract features for our model.



## Source Code of Our Model
`VAE2_ms_su.py`, `MLP_util.py`, `VAE_util.py` and `utilities.py` are the source files of our model.
`main.py` is an example of using our model.
The key points are:
- Using `model = VAE2_ms_su.VAE_SU(...)` to build the model
- Using `model.train_mlp(...)` to train the model
- Using `model.get_predict_(...)` to get prediction from the model





