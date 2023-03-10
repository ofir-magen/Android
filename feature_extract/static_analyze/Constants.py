import os

STATUS_ERR = 1
STATUS_OK = 0

from utils import read_file_to_list
from utils import read_permission_map_file_to_dict



ABS_PATH_PREFIX = os.path.join(os.path.dirname(os.getcwd()),"feature_list")

CONSTANTS = {
    'PERMISSIONS_147': {
        'MASK_BIT': 1,
        'KEYWORD': 'permission',
        'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'list_total_permissions.txt'),
        'REFERENCE_LIST': []
    },

    'INTENT_ACTIONS_126': {
        'MASK_BIT': 2,
        'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'list_total_actions.txt'),
        'REFERENCE_LIST': []
    },

    'INTENT_ACTIONS_110': {
        'MASK_BIT': 4,
        'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'list_used_actions.txt'),
        'REFERENCE_LIST': []
    },

    'COMPONENTS': {
        'MASK_BIT': 8
    },

    'SENSITIVE_APIS_106': {
        'MASK_BIT': 16,
        'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'list_used_apis.txt'),
        'REFERENCE_LIST': []
    },

    'PACKAGE_CALL_GRAPH': {
        'MASK_BIT': 32
    },

    'ANDROID_PACKAGES': {
        'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'list_android_package.txt'),
        'REFERENCE_LIST': []
    },

    'PERMISSION_MAPPINGS': {
        '16': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-16.txt'),
            'REFERENCE_DICT': {}
        },
        '17': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-17.txt'),
            'REFERENCE_DICT': {}
        },
        '18': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-18.txt'),
            'REFERENCE_DICT': {}
        },
        '19': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-19.txt'),
            'REFERENCE_DICT': {}
        },
        '20': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-21.txt'),
            'REFERENCE_DICT': {}
        },
        '21': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-21.txt'),
            'REFERENCE_DICT': {}
        },
        '22': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-22.txt'),
            'REFERENCE_DICT': {}
        },
        '23': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-23.txt'),
            'REFERENCE_DICT': {}
        },
        '24': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-24.txt'),
            'REFERENCE_DICT': {}
        },
        '25': {
            'REFERENCE_FILE': os.path.join(ABS_PATH_PREFIX, 'framework-map-25.txt'),
            'REFERENCE_DICT': {}
        }
    }
}


def _init():
    read_file_to_list(CONSTANTS['PERMISSIONS_147']['REFERENCE_LIST'],
                      CONSTANTS['PERMISSIONS_147']['REFERENCE_FILE'])
    read_file_to_list(CONSTANTS['INTENT_ACTIONS_126']['REFERENCE_LIST'],
                      CONSTANTS['INTENT_ACTIONS_126']['REFERENCE_FILE'])
    read_file_to_list(CONSTANTS['INTENT_ACTIONS_110']['REFERENCE_LIST'],
                      CONSTANTS['INTENT_ACTIONS_110']['REFERENCE_FILE'])
    read_file_to_list(CONSTANTS['SENSITIVE_APIS_106']['REFERENCE_LIST'],
                      CONSTANTS['SENSITIVE_APIS_106']['REFERENCE_FILE'])
    read_file_to_list(CONSTANTS['ANDROID_PACKAGES']['REFERENCE_LIST'],
                      CONSTANTS['ANDROID_PACKAGES']['REFERENCE_FILE'])
    # for api_level, api_dict in CONSTANTS['PERMISSION_MAPPINGS'].items():
    #     read_permission_map_file_to_dict(
    #         api_dict['REFERENCE_DICT'], api_dict['REFERENCE_FILE'])
    read_permission_map_file_to_dict(CONSTANTS['PERMISSION_MAPPINGS']['16']['REFERENCE_DICT'],
                                     CONSTANTS['PERMISSION_MAPPINGS']['16']['REFERENCE_FILE'])


_init()
