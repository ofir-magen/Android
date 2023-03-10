import os
import glob
import time
import re
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as lalg
import pickle
import heapq
from Constants import CONSTANTS
from utils import extract_spec_list_from_file
from utils import extract_sensitive_apis_list_from_smali
from utils import extract_func_call_pairs_list_from_smali
from utils import baksmali
from utils import get_filtered_vector
from utils import decomposition_apk
from utils import delete_useless_file
from utils import resolve_binary_axml_to_txt
from utils import read_file_to_list
from utils import write_list_to_file
from utils import join_class_path
from utils import EXTRACT_SPECS
from utils import COMPONENT_PATTERN
from utils import INTENT_ACTION_PATTERN
from utils import PACKAGE_PATTERN
from utils import MIN_SDK_VER_PATTERN
from utils import TARGET_SDK_VER_PATTERN
from utils import MAX_SDK_VER_PATTERN
from utils import get_cls_name_from_full_path
from utils import dense_to_sparse
from utils import get_k_largest
from Constants import STATUS_ERR
from Constants import STATUS_OK


class Extractor:
    def __init__(self, requested_features, dst_output_abs_path, src_apk_abs_path=None, is_malicisous=True):
        self.include_permissions_147 = \
            True if (requested_features &
                     CONSTANTS['PERMISSIONS_147']['MASK_BIT']) != 0 else False
        self.include_intent_actions_126 = \
            True if (requested_features &
                     CONSTANTS['INTENT_ACTIONS_126']['MASK_BIT']) != 0 else False
        self.include_intent_actions_110 = \
            True if (requested_features &
                     CONSTANTS['INTENT_ACTIONS_110']['MASK_BIT']) != 0 else False
        self.include_sensitive_apis_106 = \
            True if (requested_features &
                     CONSTANTS['SENSITIVE_APIS_106']['MASK_BIT']) != 0 else False
        self.include_components = \
            True if (requested_features &
                     CONSTANTS['COMPONENTS']['MASK_BIT']) != 0 else False
        self.include_package_call_graph = \
            True if (requested_features &
                     CONSTANTS['PACKAGE_CALL_GRAPH']['MASK_BIT']) != 0 else False
        self.requested_features = requested_features
        self.dst_output_path = dst_output_abs_path
        self.src_apk_path = src_apk_abs_path
        self.am_processed_path = os.path.join(dst_output_abs_path, 'AM_processed.txt')
        self.am_content = ''
        self.smali_dir_path = os.path.join(self.dst_output_path, 'smalis_output')
        self.feature_list = []
        self.permissions = []
        self.intent_actions = []
        self.sensitive_apis = []
        self.func_call_pairs = []

        self.is_malicious = is_malicisous
        self.package_name = ''
        self.api_level = 16
        self.min_sdk_ver = ''
        self.target_sdk_ver = ''
        self.max_sdk_ver = ''
        """ 65 * 65 """
        # self.adj_matrix = np.zeros((65, 65), dtype=np.uint8)
        """ 65 * (147 + 126) """
        # self.node_features = np.zeros((65, 273), dtype=np.uint8)
        """ 65 * 1 """
        # self.node_labels = np.zeros((65,), dtype=np.uint8)

        self.adj_matrix = None
        self.node_features = None
        self.node_labels = None
        self.nodes_num = 0

    def __fetch_permissions(self):
        """
        :return: 0 success 1 failure
        """
        self.permissions = []
        output_permissions_txt_path = os.path.join(
            self.dst_output_path, 'permissions.txt')
        if not os.path.exists(output_permissions_txt_path):
            if extract_spec_list_from_file(self.permissions, self.am_processed_path, EXTRACT_SPECS['PERMISSION']) != STATUS_OK:
                return STATUS_ERR
            write_list_to_file(self.permissions, output_permissions_txt_path)
        if (not self.permissions) and read_file_to_list(self.permissions, output_permissions_txt_path) != STATUS_OK:
            return STATUS_ERR
        else:
            get_filtered_vector(self.feature_list, self.permissions,
                                CONSTANTS['PERMISSIONS_147']['REFERENCE_LIST'])
            return STATUS_OK

    def __fetch_intent_actions(self):
        """
        :return: 0 success 1 failure
        """
        self.intent_actions = []
        output_actions_txt_path = os.path.join(
            self.dst_output_path, 'actions.txt')
        if not os.path.exists(output_actions_txt_path):
            if extract_spec_list_from_file(self.intent_actions, self.am_processed_path, EXTRACT_SPECS['ACTION']) != STATUS_OK:
                return STATUS_ERR
            write_list_to_file(self.intent_actions, output_actions_txt_path)
        if (not self.intent_actions) and read_file_to_list(self.intent_actions, output_actions_txt_path) != STATUS_OK:
            return STATUS_ERR
        else:
            if self.include_intent_actions_126:
                get_filtered_vector(self.feature_list, self.intent_actions,
                                    CONSTANTS['INTENT_ACTIONS_126']['REFERENCE_LIST'])
                return STATUS_OK
            elif self.include_intent_actions_110:
                get_filtered_vector(self.feature_list, self.intent_actions,
                                    CONSTANTS['INTENT_ACTIONS_110']['REFERENCE_LIST'])
                return STATUS_OK

    def __fetch_sensitive_apis(self):
        """
        :return: 0 success 1 failure
        """
        self.sensitive_apis = []
        output_apis_txt_path = os.path.join(self.dst_output_path, 'apis.txt')
        if not os.path.exists(output_apis_txt_path):
            smali_search_result = glob.glob(os.path.join(
                self.smali_dir_path, "**\\*.smali"), recursive=True)
            for smali_file in smali_search_result:
                if extract_sensitive_apis_list_from_smali(self.sensitive_apis, smali_file) != STATUS_OK:
                    print('extract apis failed')
                    return STATUS_ERR
            write_list_to_file(self.sensitive_apis, output_apis_txt_path)

        if (not self.sensitive_apis) and read_file_to_list(self.sensitive_apis, output_apis_txt_path) != STATUS_OK:
            return STATUS_ERR
        else:
            get_filtered_vector(self.feature_list, self.sensitive_apis,
                                CONSTANTS['SENSITIVE_APIS_106']['REFERENCE_LIST'])
            return STATUS_OK

    def __process_func(self, func_name_full_path, all_funcs, comp_dict):
        """
        get the permission features and action features
        :param func_name_full_path:
        :param all_funcs:
        :param comp_dict:
        :return:
        """
        if func_name_full_path in set(all_funcs):
            return all_funcs.index(func_name_full_path)
        all_funcs.append(func_name_full_path)
        func_idx = len(all_funcs) - 1
        # print(func_idx)
        if str(self.api_level) not in CONSTANTS['PERMISSION_MAPPINGS']:
            self.api_level = 16
        permission_mapping_dict = CONSTANTS['PERMISSION_MAPPINGS'][str(self.api_level)]
        permission_features = np.zeros((1, 147), dtype=np.uint8)
        required_permission = None
        if func_name_full_path in permission_mapping_dict:
            required_permission = permission_mapping_dict[func_name_full_path]
        if required_permission is not None and required_permission in CONSTANTS['PERMISSIONS_147']['REFERENCE_LIST']:
            permission_features[CONSTANTS['PERMISSIONS_147']['REFERENCE_LIST'].index(required_permission)] = 1
        # corresponding_cls = get_cls_name_from_full_path(func_name_full_path)
        # if corresponding_cls in comp_dict:
        #     return permission_features + comp_dict[corresponding_cls]
        # else:
        #     return permission_features + [0] * 126
        # The number of individual app components is not very large
        for comp_name, action_feature in comp_dict.items():
            if func_name_full_path.startswith(comp_name):
                self.node_features[func_idx] = np.hstack((permission_features, action_feature))
                return func_idx
        self.node_features[func_idx] = np.hstack((permission_features, np.zeros((1, 126), dtype=np.uint8)))
        return func_idx

    def __fetch_function_call_graph(self):
        """

        :return:
        """
        """ 
        Deal with the component corresponding action
        Component names in the AndroidManifest file are either complete or incomplete. If there is only one word, it is considered incomplete
        In comp_dict, key is the class name???value is the action feature value
        All methods in the class inherit this action feature   
        """
        comp_dict = {}
        for comp_match in COMPONENT_PATTERN.finditer(self.am_content):
            action_list = []
            comp_action_features = []
            comp_detail = comp_match.group(0)
            comp_name = comp_match.group('compname')
            if comp_name.startswith('.'):
                comp_name = self.package_name + comp_name
            elif len(comp_name.split('.')) == 1:
                comp_name = self.package_name + '.' + comp_name
            class_path = join_class_path(comp_name)
            for action_match in INTENT_ACTION_PATTERN.finditer(comp_detail):
                action_list.append(action_match.group('action').split('.')[-1])
            get_filtered_vector(comp_action_features, action_list, CONSTANTS['INTENT_ACTIONS_126']['REFERENCE_LIST'])
            comp_dict[class_path] = np.array(comp_action_features, dtype=np.uint8, ndmin=2)

        output_func_call_pairs_txt_path = os.path.join(
            self.dst_output_path, 'func_call_pairs.txt')
        if not os.path.exists(output_func_call_pairs_txt_path):
            temp_dict = {}
            smali_search_result = glob.glob(os.path.join(
                self.smali_dir_path, "**\\*.smali"), recursive=True)
            for smali_file in smali_search_result:
                if extract_func_call_pairs_list_from_smali(temp_dict, smali_file) != STATUS_OK:
                    print('extract func call pairs failed')
                    return STATUS_ERR
            self.func_call_pairs = list(temp_dict.keys())
            write_list_to_file(self.func_call_pairs,
                               output_func_call_pairs_txt_path)
            temp_dict.clear()
        if (not self.func_call_pairs) and read_file_to_list(self.func_call_pairs, output_func_call_pairs_txt_path) != STATUS_OK:
            return STATUS_ERR

        all_funcs_set = set()
        for call_pair in self.func_call_pairs:
            temp_list = call_pair.split(' ')
            if len(temp_list) == 3:
                all_funcs_set.add(temp_list[0])
                all_funcs_set.add(temp_list[2])
            elif len(temp_list) == 2:
                print('length 2 -> ' + ','.join(temp_list))
            elif len(temp_list) == 1:
                print('length 1 -> ' + ','.join(temp_list))
            elif len(temp_list) == 0:
                print('length 0')
            else:
                print('other length ' + str(len(temp_list)))

        # have a MainNode?????????
        self.nodes_num = len(list(all_funcs_set)) + 1
        if self.nodes_num > 30000:
            return STATUS_ERR
        all_funcs_set = None
        print('nodes num->', self.nodes_num)


        self.adj_matrix = np.zeros((self.nodes_num, self.nodes_num), dtype=np.uint8)
        self.node_features = np.zeros((self.nodes_num, 273), dtype=np.uint8)
        self.node_labels = []
        all_funcs = []
        api_lv_match = TARGET_SDK_VER_PATTERN.search(self.am_content)
        if not api_lv_match:
            api_lv_match = MIN_SDK_VER_PATTERN.search(self.am_content)
        if api_lv_match and int(api_lv_match.group('apilevel')) >= 16:
            self.api_level = api_lv_match.group('apilevel')

        # The construct mainNode is characterized by the entire app, and its tag is the tag of the app???malicious 10 benign 01
        all_funcs.append('MainNode')
        self.node_labels.append([1, 0]) if self.is_malicious else self.node_labels.append([0, 1])
        self.adj_matrix[0] = np.ones((1, self.nodes_num), dtype=np.uint8)
        self.node_features[0] = np.array(self.feature_list, dtype=np.uint8)[0:273]

        for call_pair in self.func_call_pairs:
            temp_list = call_pair.split(' ')
            if len(temp_list) == 3:
                caller = temp_list[0]
                called = temp_list[2]
                """
                Extract by API
                """

                # row :caller| column :called
                caller_idx = self.__process_func(caller, all_funcs, comp_dict)
                called_idx = self.__process_func(called, all_funcs, comp_dict)
                self.adj_matrix[caller_idx, called_idx] = 1
            elif len(temp_list) == 2:
                print('length 2 -> ' + ','.join(temp_list))
            elif len(temp_list) == 1:
                print('length 1 -> ' + ','.join(temp_list))
            elif len(temp_list) == 0:
                print('length 0')
            else:
                print('other length ' + str(len(temp_list)))
            
        write_list_to_file(all_funcs, os.path.join(self.dst_output_path, 'all_funcs.txt'))
        return STATUS_OK

    def __get_pkg_idx(self, func):
        idx = 1
        pkg_list = CONSTANTS['ANDROID_PACKAGES']['REFERENCE_LIST']
        for android_pkg_item in pkg_list:
            if func.startswith(android_pkg_item):
                caller_idx = idx
                break
            else:
                idx = idx + 1
        if idx > len(pkg_list):
            return  -1
        else:
            return caller_idx

    def __fetch_package_transfer_graph(self):
        """
        Extract by package name
        """
        # Read the adjacency matrix and list of functions
        all_funcs = []
        read_file_to_list(all_funcs, os.path.join(self.dst_output_path, 'all_funcs.txt'))
        adj = sp.csr_matrix(sp.load_npz(os.path.join(self.dst_output_path, 'adj_matrix.npz')))

        self.func_api_call_chains = [None] * len(all_funcs)

        """ 65 * 65 """ 
        pkg_adj_matrix = np.zeros((65, 65), dtype=np.uint32)
        pkg_adj_matrix[0, :] = np.ones((1, 65), dtype=np.uint32)

        for i in range(len(all_funcs))[1:adj.shape[0]]:
            paths = []
            chain = self.__fetch_call_chain_recursive(all_funcs, adj, i, paths)
            if chain is None or len(chain) == 0 or len(chain) == 1:
                continue
            for j in range(len(chain)):
                k = j + 1
                if k == len(chain):
                    break
                pkg_adj_matrix[chain[j], chain[k]] = 1 + pkg_adj_matrix[chain[j], chain[k]]

        np.save(os.path.join(self.dst_output_path, 'pkg_trans_matrix.npy'), pkg_adj_matrix)

    def __fetch_call_chain_recursive(self, all_funcs, adj, func_caller_idx, paths):
        print("depth", len(paths))
        if self.__get_pkg_idx(all_funcs[func_caller_idx]) != -1:
            return []
        if self.func_api_call_chains[func_caller_idx] is not None:
            return self.func_api_call_chains[func_caller_idx]
        # Save the traversal of non-API functions to prevent loops
        paths.append(func_caller_idx)
        api_call_chain = []
        func_called_idxs = adj[func_caller_idx].todense().tolist()[0]
        for i in range(len(func_called_idxs)):
            if func_called_idxs[i] == 0:
                continue
            if i == func_caller_idx or i in paths:
                continue
            pkg_called_idx = self.__get_pkg_idx(all_funcs[i])
            if pkg_called_idx == -1:
                api_call_chain = api_call_chain + self.__fetch_call_chain_recursive(all_funcs, adj, i, paths)
            else:
                api_call_chain.append(pkg_called_idx)
        self.func_api_call_chains[func_caller_idx] = api_call_chain
        return self.func_api_call_chains[func_caller_idx]

    def __fetch_call_chain_iteratively(self, all_funcs, adj, func_caller_idx):
        if self.__get_pkg_idx(all_funcs[func_caller_idx]) != -1:
            return []
        if self.func_api_call_chains[func_caller_idx] is not None:
            return self.func_api_call_chains[func_caller_idx]
        api_call_chain = []
        func_called_idxs = adj[func_caller_idx].todense().tolist()[0]
        for i in range(len(func_called_idxs)):
            if i == func_caller_idx:
                continue
            if func_called_idxs[i] == 1:
                pkg_called_idx = self.__get_pkg_idx(all_funcs[i])
                if pkg_called_idx == -1:
                    api_call_chain.append(pkg_called_idx)
        self.func_api_call_chains[func_caller_idx] = api_call_chain
        return self.func_api_call_chains[func_caller_idx]

    def __fetch_pkg_features(self):
        all_funcs = []
        read_file_to_list(all_funcs, os.path.join(self.dst_output_path, 'all_funcs.txt'))
        node_feat_path = os.path.join(self.dst_output_path, 'node_features.npz')
        pkg_features = np.zeros((65, 273), dtype=np.uint8)
        node_features = sp.csr_matrix(sp.load_npz(node_feat_path))
        num = node_features.shape[0]
        for i in range(len(all_funcs))[1:]:
            if i >= num:
                break
            idx = self.__get_pkg_idx(all_funcs[i]) 
            if idx == -1:
                pkg_features[0, :] = pkg_features[0, :] + node_features[i, :].todense()
            else:
                pkg_features[idx, :] = pkg_features[idx, :] + node_features[i, :].todense()
                
        np.save(os.path.join(self.dst_output_path, 'pkg_features.npy'), pkg_features)

    def __fetch_package_call_graph(self):
        """
        Extract by package name
        """
        # Read the adjacency matrix and list of functions
        all_funcs = []
        read_file_to_list(all_funcs, os.path.join(self.dst_output_path, 'all_funcs.txt'))
        adj = sp.csr_matrix(sp.load_npz(os.path.join(self.dst_output_path, 'adj_matrix.npz')))
        features = sp.csr_matrix(sp.load_npz(os.path.join(self.dst_output_path, 'node_features.npz')))

        """ 65 * 65 """ 
        pkg_adj_matrix = np.zeros((65, 65), dtype=np.uint32)
        pkg_adj_matrix[0, :] = np.ones((1, 65), dtype=np.uint32)
        """ 65 * (147 + 126) """
        pkg_node_features = np.zeros((65, 273), dtype=np.uint32)
        pkg_node_features[0, :] = np.array(np.load(os.path.join(
            self.dst_output_path, 'features_' + str(self.requested_features - 32) + '.npy'))[0:273], dtype=np.uint32)

        for i in range(len(all_funcs)):
            caller_idx = self.__get_pkg_idx(all_funcs[i])
            if caller_idx == -1:
                continue
            else:
                pkg_node_features[caller_idx, :] = pkg_node_features[caller_idx, :] + features[i, :].todense()
                called_idxs = adj[i].todense().tolist()[0]
                for j in range(len(called_idxs)):
                    if called_idxs[j] == 1:
                        called_idx = self.__get_pkg_idx(all_funcs[j])
                        pkg_adj_matrix[caller_idx, called_idx] = 1
        
        np.save(os.path.join(self.dst_output_path, 'pkg_adj_matrix.npy'), pkg_adj_matrix)
        np.save(os.path.join(self.dst_output_path, 'pkg_node_features.npy'), pkg_node_features)

    def __build_node_features(self):
        # Read the adjacency matrix and list of functions
        all_funcs = []
        read_file_to_list(all_funcs, os.path.join(self.dst_output_path, 'all_funcs.txt'))
        node_features = []
        for i in range(len(all_funcs)):
            feature_list = []
            get_filtered_vector(feature_list, all_funcs, CONSTANTS['SENSITIVE_APIS_106']['REFERENCE_LIST'])
            node_features.append(feature_list)
        sp.save_npz(os.path.join(self.dst_output_path, 'node_features_api.npz'), dense_to_sparse(np.array(node_features)))

    def __build_spectral_features(self):
        begin_time = time.time()
        adj = sp.coo_matrix(sp.load_npz(os.path.join(self.dst_output_path, 'adj_matrix.npz'))).astype(np.float32)
        d = adj.sum(1)
        l = d - adj
        try:
            eigen_vals, eigen_vecs = lalg.eigs(l, k=6)
        except:
            return STATUS_ERR
        sorted_eigen_vals = np.sort(eigen_vals)
        eigen_vals = eigen_vals.tolist()
        sorted_eigen_vals = sorted_eigen_vals.tolist()
        k_vecs = []
        for i in range(6):
            idx = eigen_vals.index(sorted_eigen_vals[5-i])
            k_vecs.append(eigen_vecs[:, idx])
        cos_vals = []
        for i in range(6):
            for j in range(6)[i+1:]:
                vector1 = k_vecs[i]
                vector2 = k_vecs[j]
                cos_vals.append(np.dot(vector1,vector2)/(np.linalg.norm(vector1)*(np.linalg.norm(vector2))))
        np.save(os.path.join(self.dst_output_path, 'spectral_features_6.npy'), np.abs(np.array(cos_vals)))
        print(time.time() - begin_time)

    def __check_prerequisites(self):
        # if not os.path.exists(self.src_apk_path):
        #     raise FileNotFoundError
        if not os.path.exists(self.dst_output_path):
            os.makedirs(self.dst_output_path)
            decomposition_apk(self.dst_output_path, self.src_apk_path)
            delete_useless_file(self.dst_output_path)
        raw_am_path = os.path.join(self.dst_output_path, 'AndroidManifest.xml')
        if not os.path.exists(raw_am_path):
            print('raw manifest not exist(decomposition failed)')
            return STATUS_ERR
        if not os.path.exists(self.am_processed_path) and resolve_binary_axml_to_txt(
            self.am_processed_path, os.path.join(self.dst_output_path, 'AndroidManifest.xml')) == STATUS_ERR:
                return STATUS_ERR
        try:
            with open(self.am_processed_path, 'r') as f:
                self.am_content = f.read()
        except:
            return STATUS_ERR    
        pkg_match = PACKAGE_PATTERN.search(self.am_content)
        if pkg_match is None:
            print('cannot find package name')
            return STATUS_ERR
        self.package_name = pkg_match.group('pkgname')

        if (self.include_sensitive_apis_106 or self.include_package_call_graph) and not os.path.exists(
                self.smali_dir_path):
            # Extract all smali from all dex
            # If the SMALIS_OUTPUT directory does not exist, use BAKSMALI to process the DEX file to get the SMALI file
            # Smali files will be extracted after all Dex files are processed
            dex_search_result = glob.glob(os.path.join(
                self.dst_output_path, "*.dex"), recursive=False)
            for dex_file in dex_search_result:
                if baksmali(dex_file, self.smali_dir_path) != STATUS_OK:
                    print('one of baksmali ops failed')
                    return STATUS_ERR
        return STATUS_OK

    def __fetch_package_name(self):
        try:
            with open(self.am_processed_path, 'r') as f:
                content = f.read()
                pattern = re.compile('package=.+')
                results = pattern.findall(content)
                if len(results) != 0:
                    self.package_name = results[0].split('=')[1].strip('\"')
                    return STATUS_OK
                else:
                    return STATUS_ERR
        except:
            return STATUS_ERR

    def get_result(self):

        print('processing ' + os.path.split(self.dst_output_path)[-1])

        list_feature_file_path = os.path.join(
            self.dst_output_path, 'features_379' + '.npy')
        dense_adj_mat_path = os.path.join(self.dst_output_path, 'adj_matrix.npy')
        dense_node_feat_path = os.path.join(self.dst_output_path, 'node_features.npy')
        adj_mat_path = os.path.join(self.dst_output_path, 'adj_matrix.npz')
        node_feat_path = os.path.join(self.dst_output_path, 'node_features.npz')
        if os.path.exists(list_feature_file_path) and os.path.exists(adj_mat_path) and os.path.exists(node_feat_path):
            return STATUS_OK
        if os.path.exists(list_feature_file_path) and os.path.exists(dense_adj_mat_path) and os.path.exists(dense_node_feat_path):
            sp.save_npz(adj_mat_path, dense_to_sparse(np.load(dense_adj_mat_path)))
            sp.save_npz(node_feat_path, dense_to_sparse(np.load(dense_node_feat_path)))
            os.remove(dense_adj_mat_path)
            os.remove(dense_node_feat_path)
            return STATUS_OK
        if self.__check_prerequisites() != STATUS_OK:
            print('prerequisites not satisfied')
            return STATUS_ERR
        if self.include_permissions_147 and self.__fetch_permissions() != STATUS_OK:
            print('fetch permissions failed')
            return STATUS_ERR
        if (self.include_intent_actions_126 or self.include_intent_actions_110) and self.__fetch_intent_actions() != STATUS_OK:
            print('fetch intent actions failed')
            return STATUS_ERR
        if self.include_sensitive_apis_106 and self.__fetch_sensitive_apis() != STATUS_OK:
            print('fetch sensitive apis failed')
            return STATUS_ERR


        np.save(list_feature_file_path, np.array(self.feature_list, dtype=np.uint8))


        print('processing ' + os.path.split(self.dst_output_path)[-1])

        list_feature_file_path = os.path.join(
            self.dst_output_path, 'features_379' + '.npy')
        if os.path.exists(list_feature_file_path):
            return STATUS_OK
        else:
            return STATUS_ERR

