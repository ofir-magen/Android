import os
import time
import multiprocessing
import sys
from Constants import CONSTANTS
from extract_ops import Extractor

permissions_147 = CONSTANTS['PERMISSIONS_147']['MASK_BIT']
intent_actions_126 = CONSTANTS['INTENT_ACTIONS_126']['MASK_BIT']
intent_actions_110 = CONSTANTS['INTENT_ACTIONS_110']['MASK_BIT']
components = CONSTANTS['COMPONENTS']['MASK_BIT']
sensitive_apis_106 = CONSTANTS['SENSITIVE_APIS_106']['MASK_BIT']
package_call_graph = CONSTANTS['PACKAGE_CALL_GRAPH']['MASK_BIT']

requested_features = permissions_147 | intent_actions_126 | sensitive_apis_106 

def extract_task(apk_abs_path):
    parent_dir = os.path.join(os.path.dirname(os.getcwd()),"dataset")
    dst_output_abs_path = os.path.join(parent_dir, apk_abs_path.split('.')[0])
    extractor = Extractor(requested_features, dst_output_abs_path, src_apk_abs_path=apk_abs_path)
    result = extractor.get_result()
    if result == 1:
        print('error', '~~~', os.path.split(dst_output_abs_path)[-1], '~~~', time.asctime())
    else:
        print('ok', '~~~', os.path.split(dst_output_abs_path)[-1], '~~~', time.asctime())


if __name__ == '__main__':

    root_dir = os.path.join(os.path.dirname(os.getcwd()),"dataset")
    apk_to_process = [root_dir + '\\' + i for i in os.listdir(root_dir)]

    for i in apk_to_process:
        extract_task(i)
