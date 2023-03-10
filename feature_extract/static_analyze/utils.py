import os
import re
import shutil
import glob
import random
import numpy as np
import scipy.sparse as sp
from Config import Config
from Constants import STATUS_ERR
from Constants import STATUS_OK

SENSITIVE_API_PATTERN = re.compile(
    '(?P<api>Landroid/(?:accounts|app|content|hardware|location|media|mtp|net|os|provider|telephony|drm).+;->.+)(?:\()')
INVOKE_PATTERN = re.compile(
    '(?P<invoketype>invoke-(?:virtual|direct|static|super|interface)) (?:\{.*\}), (?P<method>L.+;->.+)(?:\()')
METHOD_BLOCK_PATTERN = re.compile('\.method.* (?P<methodname>.*)\(.*\n((?:.|\n)*?)\.end method')
CLASS_NAME_PATTERN = re.compile('\.class.*(?P<clsname>L.*)(?:;)')
API_PERMISSION_MAPPING_PATTERN = re.compile('(?P<api>.*)\(.*::\s+(?P<permission>.+)')
MIN_SDK_VER_PATTERN = re.compile('minSdkVersion=\"(?P<apilevel>\d+)\"')
TARGET_SDK_VER_PATTERN = re.compile('targetSdkVersion=\"(?P<apilevel>\d+)\"')
MAX_SDK_VER_PATTERN = re.compile('maxSdkVersion=\"(?P<apilevel>\d+)\"')
PERMISSION_PATTERN = re.compile('uses-permission\s+android:name=\"(?P<permission>.+)\"')
INTENT_ACTION_PATTERN = re.compile('action\s+android:name=\"(?P<action>.+)\"')
COMPONENT_PATTERN = re.compile(
    '<(activity|service|receiver|provider)((?:.|\n)+?)android:name=\"(?P<compname>.+)\"((?:.|\n)+?)</\\1>')
PACKAGE_PATTERN = re.compile('manifest((?:.|\n)+?)package=\"(?P<pkgname>.+)\"')
EXTRACT_SPECS = {
    'PERMISSION': 0,
    'ACTION': 1
}


def write_list_to_file(source_list, file_abs_path):
    """
    Writes the contents of the source list array to a file, one line per element
    :param source_list:
    :param file_abs_path:
    :return:
    """
    with open(file_abs_path, 'w', encoding='utf-8') as f:
        try:
            for item in source_list:
                f.write(str(item))
                f.write("\n")
            return STATUS_OK
        except UnicodeDecodeError:
            return STATUS_ERR


def read_file_to_list(target_list, file_abs_path):
    """
    Reads the contents of the file line by line into the target list
    :param target_list:
    :param file_abs_path:
    :return:
    """
    target_list.clear()
    with open(file_abs_path, 'r') as f:
        try:
            for line in f.readlines():
                line = line.rstrip('\n')
                if line == '':
                    continue
                target_list.append(line)
            return STATUS_OK
        except UnicodeDecodeError:
            return STATUS_ERR


def extract_spec_list_from_file(target_list, file_abs_path, spec):
    """
    Extract the specific contents of the file and put them into the target list
    :param target_list:
    :param file_abs_path:
    :param spec:
    :return:
    """
    # target_list.clear()
    # with open(file_abs_path, 'r') as f:
    #     try:
    #         for line in f.readlines():
    #             line = line.rstrip('\n')
    #             line = line.rstrip('\"')
    #             temp = line.split('.')
    #             if keyword in temp:
    #                 target_list.append(temp[-1])
    #         return 0
    #     except UnicodeDecodeError:
    #         return 1
    target_list.clear()
    with open(file_abs_path, 'r') as f:
        try:
            s = f.read()
            if spec == EXTRACT_SPECS['PERMISSION']:
                for match in PERMISSION_PATTERN.finditer(s):
                    target_list.append(match.group('permission').split('.')[-1])
            elif spec == EXTRACT_SPECS['ACTION']:
                for match in INTENT_ACTION_PATTERN.finditer(s):
                    target_list.append(match.group('action').split('.')[-1])
            return STATUS_OK
        except UnicodeDecodeError:
            return STATUS_ERR


def extract_sensitive_apis_list_from_smali(target_list, smali_file_abs_path):
    """
    Extracts the Android system API calls from the given Smali file
    :param target_list:
    :param smali_file_abs_path:
    :return: 
    """
    try:
        with open(smali_file_abs_path, 'r') as f:
            s = f.read()
            for match in SENSITIVE_API_PATTERN.finditer(s):
                if match.group('api') not in target_list:
                    target_list.append(match.group('api'))
        return STATUS_OK
    except UnicodeDecodeError:
        try:
            with open(smali_file_abs_path, 'r', encoding='utf-8') as f:
                s = f.read()
                # results = Config['API_RE_PATTERN'].findall(s)
                # for item in results:
                #     if item[:-1] not in target_list:
                #         target_list.append(item[:-1])
                for match in SENSITIVE_API_PATTERN.finditer(s):
                    if match.group('api') not in target_list:
                        target_list.append(match.group('api'))
            return STATUS_OK
        except:
            return STATUS_ERR


def extract_func_call_pairs_list_from_smali(target_dict, smali_file_abs_path):
    """
    Extract function calls from the Smali file , format is  Lpack1/class1;->func1 invoke-type Lpack2/class2;->func2
    :param target_list:
    :param smali_file_abs_path:
    :return:
    """
    try:
        with open(smali_file_abs_path, 'r') as f:
            s = f.read()
            class_name_match = CLASS_NAME_PATTERN.search(s)
            class_name = class_name_match.group(
                'clsname') if class_name_match is not None else ''
            for method_block_match in METHOD_BLOCK_PATTERN.finditer(s):
                method_name = method_block_match.group('methodname')
                for invoke_match in INVOKE_PATTERN.finditer(method_block_match.group()):
                    cur_pair = class_name + ';->' + method_name + ' ' + \
                               invoke_match.group('invoketype') + \
                               ' ' + invoke_match.group('method')
                    target_dict[cur_pair] = ''
        return STATUS_OK
    except UnicodeDecodeError:
        try:
            with open(smali_file_abs_path, 'r', encoding='utf-8') as f:
                s = f.read()
                class_name_match = CLASS_NAME_PATTERN.search(s)
                class_name = class_name_match.group(
                    'clsname') if class_name_match is not None else ''
                for method_block_match in METHOD_BLOCK_PATTERN.finditer(s):
                    method_name = method_block_match.group('methodname')
                    for invoke_match in INVOKE_PATTERN.finditer(method_block_match.group()):
                        cur_pair = class_name + ';->' + method_name + ' ' + invoke_match.group(
                            'invoketype') + ' ' + invoke_match.group('method')
                        target_dict[cur_pair] = ''
            return STATUS_OK
        except:
            return STATUS_ERR


def baksmali(dex_file_abs_path, smali_output_abs_path):
    """
    Unpack the dex file using baksmali to get the.smali file used to extract the API calls
    :param dex_file_abs_path:
    :return:
    """
    if os.system(
            'java -jar ' + Config['BAK_SMALI_PATH'] + ' d ' + dex_file_abs_path + ' -o ' + smali_output_abs_path) != 0:
        return STATUS_ERR
    else:
        return STATUS_OK


def get_filtered_vector(target_list, extracted_list, reference_list):
    """
    Search the extracted_list for each item in the reference_list, adding 1 if present in the target_list, or 0 if not
    :param target_list:  feature vector
    :param extracted_list:
    :param reference_list:
    """
    for item in reference_list:
        if item in extracted_list:
            target_list.append(1)
        else:
            target_list.append(0)


def resolve_binary_axml_to_txt(target_txt_abs_path, source_axml_abs_path):
    """
    Parse the binary AndroidManifest.xml file as text

    :param target_txt_abs_path:
    :param source_axml_abs_path:
    :return:
    """
    if os.system('java -jar ' + Config[
        'AXML_PRINTER_PATH'] + ' ' + source_axml_abs_path + ' >> ' + target_txt_abs_path) != 0:
        return STATUS_ERR
    else:
        if os.path.exists(target_txt_abs_path):
            with open(target_txt_abs_path, 'r') as f:
                if len(f.readlines()) < 2:
                    return STATUS_ERR
                else:
                    return STATUS_OK
        else:
            return STATUS_ERR


def decomposition_apk(target_dir_abs_path, source_apk_abs_path):
    """
    Unpacking the APK file using APKTool has the same effect as unpacking the APK file directly
    :param target_dir_abs_path:
    :param source_apk_abs_path:
    :return:
    """
    os.system(Config['APK_TOOL_PATH'] + ' d -f -r -s -o ' +
              target_dir_abs_path + ' ' + source_apk_abs_path)


def disassemble_dex(target_output_abs_path, source_dex_abs_path):
    """
    Decompile the dex bytecode file using baksmali.jar to get the.smali file
    :param target_output_abs_path:
    :param source_dex_abs_path:
    :return:
    """
    os.system('java -jar ' + Config['BAK_SMALI_PATH'] + ' disassemble ' +
              source_dex_abs_path + ' -o ' + target_output_abs_path)


def compute_sha256(source_apk_abs_path):
    """
    Call 7zip to calculate the SHA256 of APK
    :param target_text:
    :param source_apk_abs_path:
    :return: 1 failure
    """
    result_string = os.popen(
        Config['7Z_PATH'] + ' h -scrcSHA256 ' + source_apk_abs_path).read()
    sha256 = ' '
    for l in result_string.split('\n'):
        if l.startswith('SHA256 for data:'):
            sha256 = re.split(r' +', l)[-1]
            break
    return sha256 if sha256 != ' ' else 1


def delete_useless_file(apk_files_dir):
    """
    The file obtained by unpacking APK contains resource files that occupy a large amount of space. These files are not useful for static analysis, so they are deleted
    Some APKs include.dex files in the assets directory for dynamic loading. This.dex file is required for static analysis, so it is kept
    :param apk_files_dir:
    :return:
    """
    seed = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for sub_dir_path, sub_dir_names, sub_file_names in os.walk(apk_files_dir):
        for item in sub_file_names:
            if item != 'AndroidManifest.xml' and not item.endswith('.dex'):
                os.remove(os.path.join(apk_files_dir, item))
        for item in sub_dir_names:
            if item == 'assets':
                search_result = glob.glob(os.path.join(
                    apk_files_dir, "assets\\**\\*.dex"), recursive=True)
                if len(search_result) != 0:
                    for dex_file in search_result:
                        rand_arr = []
                        for i in range(8):
                            rand_arr.append(random.choice(seed))
                        random_file_name = ''.join(rand_arr)
                        shutil.move(dex_file, os.path.join(
                            apk_files_dir, random_file_name + ".dex"))
            # shutil.rmtree(os.path.join(apk_files_dir, item))
            os.system('rd /s /q ' + os.path.join(apk_files_dir, item))


def join_class_path(dot_sep_str):
    """
    :param dot_sep_str:
    :return:
    """
    return 'L' + '/'.join(dot_sep_str.split('.'))


def get_cls_name_from_full_path(full_path_api):
    """
    Split the class name from the full-path API
    :param full_path_api:
    :return:
    """
    temp_list = full_path_api.split(';')
    return temp_list[0]


def read_permission_map_file_to_dict(target_dict, map_file_abs_path):
    # Is there ever a case where an API requires multiple permissions?
    # There is a duplicate, ignore it
    with open(map_file_abs_path, 'r', encoding='utf-8') as f:
        s = f.read()
        for match in API_PERMISSION_MAPPING_PATTERN.finditer(s):
            temp_list = match.group('api').split('.')
            api = 'L' + '/'.join(temp_list[0:-1]) + ';->' + temp_list[-1]
            target_dict[api] = match.group('permission').split('.')[-1]


def dense_to_sparse(dense_ndarray):
    return sp.coo_matrix(dense_ndarray)


def get_k_largest(eigen_vals, k):
    lst = eigen_vals.copy()
    indices = []
    for i in range(k):
        indices.append(lst.index(max(lst)))
        lst[indices[-1]] = float('-inf')
    return indices
