# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


import os
import unittest

from pkg.utils import custom_getenv


class TestCustomGetenv(unittest.TestCase):

    def setUp(self):
        os.environ['TEST_INTEGER'] = '123'
        os.environ['TEST_FLOAT'] = '123.45'
        os.environ['TEST_BOOLEAN'] = 'true'
        os.environ['TEST_STRING'] = '"Hello, World!"'
        os.environ['TEST_LIST'] = '[1, 2, 3]'
        os.environ['TEST_DICT'] = '{"key": "value"}'
        os.environ['TEST_INVALID_JSON'] = 'invalid json'

    def tearDown(self):
        del os.environ['TEST_INTEGER']
        del os.environ['TEST_FLOAT']
        del os.environ['TEST_BOOLEAN']
        del os.environ['TEST_STRING']
        del os.environ['TEST_LIST']
        del os.environ['TEST_DICT']
        del os.environ['TEST_INVALID_JSON']

    def test_custom_getenv_integer(self):
        self.assertEqual(custom_getenv('TEST_INTEGER'), 123)

    def test_custom_getenv_float(self):
        self.assertEqual(custom_getenv('TEST_FLOAT'), 123.45)

    def test_custom_getenv_boolean(self):
        self.assertEqual(custom_getenv('TEST_BOOLEAN'), True)

    def test_custom_getenv_string(self):
        self.assertEqual(custom_getenv('TEST_STRING'), "Hello, World!")

    def test_custom_getenv_list(self):
        self.assertEqual(custom_getenv('TEST_LIST'), [1, 2, 3])

    def test_custom_getenv_dict(self):
        self.assertEqual(custom_getenv('TEST_DICT'), {"key": "value"})

    def test_custom_getenv_invalid_json(self):
        self.assertEqual(custom_getenv('TEST_INVALID_JSON'), 'invalid json')

    def test_custom_getenv_default(self):
        self.assertEqual(custom_getenv('NON_EXISTENT_KEY', 'default_value'), 'default_value')

if __name__ == '__main__':
    unittest.main()