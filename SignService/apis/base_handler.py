# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：  
# 1. 不得用于任何商业用途。  
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。  
# 3. 不得进行大规模爬取或对平台造成运营干扰。  
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。   
# 5. 不得用于任何非法或不当的用途。
#   
# 详细许可条款请参阅项目根目录下的LICENSE文件。  
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。  


# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, Union

from pydantic import BaseModel, ValidationError
from tornado.web import RequestHandler

import constant
import context_vars
from constant.error_code import ApiCode
from params.base_model import ErrorResponseModel, OkResponseModel
from pkg import utils
from pkg.custom_exceptions import ReturnValueError


class BaseRequestHandler(RequestHandler):
    def prepare(self):
        """
        请求入口的前置处理
        :return:
        """
        request_id: str = self.request.headers.get(constant.REQUEST_ID_HEADERS_KEY) or utils.get_uuid_md5_value()
        context_vars.request_id_var.set(request_id)

    def is_json_request(self) -> bool:
        """
        判断请求是否是json请求
        :return:
        """
        is_content_type_json = self.request.headers.get("content-type", "").find("application/json") != -1
        response_type = self.request.headers.get(constant.RESPONSE_TYPE_JSON_HEADERS_KEY)
        if is_content_type_json or response_type == constant.RESPONSE_TYPE_JSON_HEADERS_VALUE:
            return True
        return False


class BaseAPIHandler(BaseRequestHandler):
    result_model = BaseModel

    def check_xsrf_cookie(self):
        pass

    @staticmethod
    def set_error_code(errorcode, extra=None):
        """
        设置错误码
        :param errorcode:
        :param extra:
        :return:
        """
        if extra is None:
            extra = {}
        if isinstance(errorcode, ApiCode):
            errorcode = errorcode.value
        message = ApiCode.get_message(errorcode)
        response = ErrorResponseModel(biz_code=errorcode, msg=message, extra=extra)
        return response

    @staticmethod
    def set_error_code_with_extra_msg(errorcode, msg, extra=None):
        """
        设置错误码
        :param errorcode: 错误码
        :param msg: 错误信息
        :param extra: 额外信息
        :return:
        """
        if extra is None:
            extra = {}
        message = ApiCode.get_message(errorcode)
        full_msg = f"{message} {msg}" if msg else message
        response = ErrorResponseModel(biz_code=errorcode, msg=full_msg, extra=extra)
        return response

    @staticmethod
    def set_error_info(errorcode, errmsg, extra=None):
        """
        设置错误信息
        :param errorcode: 错误吗
        :param errmsg: 错误信息
        :param extra: 额外信息
        :return:
        """
        if extra is None:
            extra = {}
        response = ErrorResponseModel(biz_code=errorcode, msg=errmsg, extra=extra)
        return response

    def set_ok_res(self, data: Union[BaseModel, Dict[str, Any], Any], msg='OK!'):
        """
        设置成功响应
        :param data:
        :param msg:
        :return:
        """
        # 如果是BaseModel的子类，判断result_model的指向是否是BaseModel，如果不是，则证明子类定义的有响应模型
        if self.result_model and self.result_model != BaseModel:
            data = self.result_model.model_validate(data)
            response = OkResponseModel(data=data.model_dump(), msg=msg)
            return response

        # 如果在传递的data是BaseModel的子类，则说明子类在调用return_ok的时候，传递了一个BaseModel的子类,需要转换成dict
        if data and isinstance(data, BaseModel):
            data = data.model_dump()

        # 否则，直接返回data
        response = OkResponseModel(data=data, msg=msg)
        return response

    def return_error(self, errorcode, extra=None):
        """
        返回错误信息
        :param errorcode:
        :param extra:
        :return:
        """
        if extra is None:
            extra = {}
        response = self.set_error_code(errorcode, extra)
        self.set_header("Content-Type", "application/json")
        self.write(response.model_dump_json())
        self.finish()

    def return_error_info(self, errorcode, errmsg, extra=None):
        """
        返回错误信息，可以自定义错误信息
        :param errorcode:
        :param errmsg:
        :param extra:
        :return:
        """
        if extra is None:
            extra = {}
        response = self.set_error_info(errorcode, errmsg, extra)
        self.set_status(500)
        self.set_header("Content-Type", "application/json")
        self.write(response.model_dump_json())
        self.finish()

    def return_error_with_extra_msg(self, errorcode, errmsg, extra=None):
        """
        返回错误信息，可以自定义错误信息
        :param errorcode:
        :param errmsg:
        :param extra:
        :return:
        """
        if extra is None:
            extra = {}
        response = self.set_error_code_with_extra_msg(errorcode, errmsg, extra)
        self.set_status(500)
        self.set_header("Content-Type", "application/json")
        self.write(response.model_dump_json())
        self.finish()

    def return_ok(self, data=None, msg='OK!'):
        """
        返回成功信息
        :param data:
        :param msg:
        :return:
        """
        if data is None:
            data = {}
        response = self.set_ok_res(data, msg)
        self.set_header("Content-Type", "application/json")
        self.write(response.model_dump_json())
        self.finish()


class TornadoBaseReqHandler(BaseAPIHandler):
    request_model = BaseModel

    def prepare(self):
        """
        请求入口的前置处理
        :return:
        """
        super().prepare()
        self.request_data = {}
        content_type = self.request.headers.get("Content-Type", "")
        if self.is_json_request():
            try:
                body_dict = json.loads(self.request.body.decode("utf-8"))
                self.request_data.update(body_dict)
            except json.JSONDecodeError:
                pass
            except UnicodeDecodeError:
                pass
            return

        # 如果request_model中定义了List[str]类型的参数,需要使用tornado的self.get_arguments方法获取参数
        if self.request_model and self.request_model.__annotations__:
            for k, v in self.request_model.__annotations__.items():
                # getattr(field_type, '__origin__', None)会返回泛型类型的原始类型，比如List[str]的原始类型是list
                if getattr(v, '__origin__', None) is list and k not in self.request_data:
                    self.request_data[k] = self.get_arguments(k)

        self.request_data.update(
            {k: self.get_argument(k) for k in self.request.arguments if k not in self.request_data})
        if "multipart/form-data" in content_type:
            for k, v in self.request.files.items():  # 如果是文件上传，需要将文件信息也加入到request_data中
                self.request_data[k] = v

    def get_path_params(self) -> Dict[str, Any]:
        """
        获取路径参数
        :return:
        """
        return {k: self.path_kwargs.get(k) for k in self.path_kwargs}

    def get_query_params(self) -> Dict[str, Any]:
        """
        获取查询参数
        :return:
        """
        return {k: self.get_argument(k) for k in self.request.arguments}

    def parse_params(self) -> Any:
        """
        解析参数，校验参数，如果参数校验失败，返回错误信息，不再继续执行，携带额外信息
        子类集成的时候，需要定义request_model的类属性
        :return:
        """
        try:
            data = {**self.get_path_params(), **self.get_query_params(), **self.request_data}
            return self.request_model.model_validate(data)
        except ValidationError as e:
            self.set_status(400)
            self.return_error(ApiCode.INVALID_PARAMETER, extra=json.loads(e.json()))

    def response_data(self, template_name: str = None, data: Dict[str, Any] = None, msg: str = 'OK!'):
        """
        在父类定义一个response_data,根据请求头中的x-response-type-json来判断是否返回json数据，如果这个值不存在，则返回html
        :param template_name:
        :param data:
        :param msg:
        :return:
        """
        if self.is_json_request():
            self.return_ok(data, msg=msg)
            return

        if data is not None and template_name:
            self.render(template_name, **data)
            return

        raise ReturnValueError("response_data need template_name and data")


class PongHandler(TornadoBaseReqHandler):
    async def get(self):
        self.return_ok(data={"message": "pong"})