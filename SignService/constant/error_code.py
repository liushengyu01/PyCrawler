# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


from enum import Enum


class ApiCode(Enum):
    OK = (0, '成功!')
    ERROR = (1, '错误!')
    EXCEPTION = (2, '异常!')
    INVALID_PARAMETER = (3, '无效参数!')
    MISSING_PARAMETER = (4, '缺少参数!')
    FAILED_TO_ADD = (5, '添加记录失败!')
    FAILED_TO_UPDATE = (6, '更新记录失败!')
    EMPTY_RESULT = (7, '结果为空!')
    NO_PERMISSION_TO_ACCESS = (519, '无访问权限!')

    def __new__(cls, code, message):
        obj = object.__new__(cls)
        obj._value_ = code
        obj.message = message
        return obj

    @classmethod
    def get_message(cls, code) -> str:
        for api_code in cls:
            if api_code.value == code:
                return api_code.message
        return '未知错误代码'

if __name__ == '__main__':
    # 使用
    errorcode = ApiCode.INVALID_PARAMETER
    message = ApiCode.get_message(errorcode.value)
    print(message)  # 输出: 无效参数!