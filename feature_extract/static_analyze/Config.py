import os
import re
#tools root path
TOOLS_PATH_PREFIX = os.path.join(os.path.dirname(os.getcwd()),"tools")
print(TOOLS_PATH_PREFIX)


Config = {
    'APK_TOOL_PATH': os.path.join(TOOLS_PATH_PREFIX, 'apktool.bat'),
    'AXML_PRINTER_PATH': os.path.join(TOOLS_PATH_PREFIX, 'AXMLPrinter2.jar'),
    'BAK_SMALI_PATH': os.path.join(TOOLS_PATH_PREFIX, 'baksmali-2.2.4.jar'),

}
