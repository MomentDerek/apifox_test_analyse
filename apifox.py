# -*- coding: UTF-8 -*-
import json  # 标准库 json 主要用于 JSON 数据的读取和写入，而不提供直接的 JSONPath 功能
import os
import re
import subprocess
from datetime import datetime

import requests
from jsonpath_ng import parse  # 专门的 JSONPath 解析库

import config


def send_message(
    message="",
    report_url=None,
    is_success=True,
    total_fail_case_info: dict[str, dict] = None,
):
    """通过webhook发送消息，online是false就发通知给测试群"""
    # message_json = json.dumps(message)
    if total_fail_case_info is None:
        total_fail_case_info = {}
    if report_url is None:
        report_url = [""]
    fail_info = []
    if not is_success:
        fail_info = [
            {
                "tag": "column_set",
                "flex_mode": "none",
                "background_style": "default",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "center",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"content": "用例名", "tag": "plain_text"},
                            }
                        ],
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "center",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"content": "接口路径", "tag": "plain_text"},
                            }
                        ],
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 2,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "div",
                                "text": {"content": "错误原因", "tag": "plain_text"},
                            }
                        ],
                    },
                ],
                "horizontal_spacing": "default",
            }
        ]
        fail_info.extend(
            [
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "background_style": "grey",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "vertical_align": "center",
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {"content": key, "tag": "plain_text"},
                                }
                            ],
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "vertical_align": "center",
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "content": f"{item['接口地址']}",
                                        "tag": "plain_text",
                                    },
                                }
                            ],
                        },
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 2,
                            "vertical_align": "top",
                            "elements": [
                                {
                                    "tag": "div",
                                    "text": {
                                        "content": f"{item['错误内容']}",
                                        "tag": "plain_text",
                                    },
                                }
                            ],
                        },
                    ],
                    "horizontal_spacing": "default",
                }
                for key, item in total_fail_case_info.items()
            ]
        )
    data = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": "测试完成",
                    "tag": "plain_text",
                },
                "template": "blue",
            },
            "elements": [
                {"tag": "div", "text": {"content": message, "tag": "plain_text"}},
                *fail_info,
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": f"测试报告{i+1 if len(report_url)>1 else ''}",
                            },
                            "url": url,
                            "type": "primary",
                        }
                        for i, url in enumerate(report_url)
                    ],
                },
            ],
        },
    }
    if not is_success:
        data["card"]["header"]["title"]["content"] = "测试失败"
        data["card"]["header"]["template"] = "red"
        data["card"]["elements"].append(
            {"tag": "div", "text": {"content": "<at id=all></at>", "tag": "lark_md"}}
        )
    request_body = json.dumps(data, ensure_ascii=False)
    webhook_url_test = "https://open.larksuite.com/open-apis/bot/v2/hook/1b6a8626-307e-4297-a0a3-919a3e809aee"
    response = requests.post(
        webhook_url_test,
        data=request_body,
        headers={"Content-Type": "application/json"},
    )
    # 检查响应结果
    if response.status_code == 200 and json.loads(response.content)["code"] == 0:
        print("Message sent successfully.")
    else:
        print(
            f"Failed to send message. Status code: {json.loads(response.content)['code']}"
        )
    print(f"response: {response.content}")


def json_analyse(filename="apifox-report-2023-09-12-17-20-08-602-0.json"):
    """分析输出的json报告"""
    path = "apifox-reports/"
    file_path = path + filename
    if ".json" not in file_path:
        file_path += ".json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as json_file:
                # 使用 json.load() 解析 JSON 文件内容为 Python 数据结构
                data = json.load(json_file)
            # 现在，'data' 变量包含了 JSON 文件中的数据，可以像访问字典一样访问其中的内容
            total_count = data["result"]["stats"]["requests"]["total"]
            fail_count = data["result"]["stats"]["requests"]["failed"]
            result_url = [
                match.value
                for match in parse("$.collection.testReportInfoUrlPath").find(data)
            ]
            result_dict = {}
            jsonpath_expr = parse("$.collection.name")  # 取外部的整个测试用例集的名字
            # 使用 JSONPath 表达式提取数据
            matches_fail_case_parent = [
                match.value if match.value else "None"
                for match in jsonpath_expr.find(data)
            ]
            if matches_fail_case_parent:
                matches_fail_case_parent = matches_fail_case_parent[0]
            # 定义 JSONPath 表达式
            jsonpath_expr = parse("$.result.steps[*].id")
            case_id = [match.value for match in jsonpath_expr.find(data)]
            jsonpath_expr = parse("$.result.steps[*].name")
            case_name = [match.value for match in jsonpath_expr.find(data)]
            jsonpath_expr = parse("$.result.steps[*].metaInfo.httpApiPath")
            case_url = [match.value for match in jsonpath_expr.find(data)]
            # 先把整个用例的数据取出来，用来做下面报错数据的映射
            cases_dict = {
                id_: (name, url)
                for id_, name, url in zip(case_id, case_name, case_url)
            }
            if fail_count > 0:
                # 把数据生成一个字典用来做下面的匹对
                # print(cases_dict)
                jsonpath_expr = parse("$.result.failures[*].error.message")
                matches_fail_reason = [
                    match.value for match in jsonpath_expr.find(data)
                ]
                jsonpath_expr = parse("$.result.failures[*].cursor.ref")
                matches_fail_case_id = [
                    match.value for match in jsonpath_expr.find(data)
                ]
                # print(matches_fail_case_id)
                matches_fail_case = []
                # 遍历失败ID列表
                j = 0
                for fail_id in matches_fail_case_id:
                    # 检查fail_id是否在cases_dict中
                    if fail_id in cases_dict:
                        # 从字典中获取case_name和case_url
                        case_name, case_url = cases_dict[fail_id]
                        # 创建一个包含所需信息的字典或元组，并将其添加到列表中
                        # 这里使用字典作为示例
                        matches_fail_case.append(
                            {
                                "case_name": case_name,
                                "case_url": case_url,
                                "fail_reason": matches_fail_reason[
                                    j
                                ],  # 获取对应的失败原因
                            }
                        )
                    j += 1
                for i in range(len(matches_fail_case)):
                    fail_case = matches_fail_case[i]
                    fail_case_name = fail_case["case_name"]
                    fail_reason = fail_case["fail_reason"]
                    fail_case_parent = matches_fail_case_parent
                    fail_path = fail_case["case_url"]
                    # 如果已存在，则取出之前的dict，并在错误内容后附加新的错误内容
                    if fail_case_name in result_dict:
                        result_dict[fail_case_name]["错误内容"] += (
                                "\n" + fail_reason
                        )
                    else:
                        result_dict[fail_case_name] = {
                            "错误内容": fail_reason,
                            "测试用例集": fail_case_parent,
                            "接口地址": fail_path,
                        }
            return total_count, fail_count, result_dict, result_url
        except json.decoder.JSONDecodeError as e:
            print(f"JSON解析错误：{str(e)}")
            return False
        except Exception as e:
            print(e)
            return False


class apifox_auto_test:
    def __init__(self):
        self.total_case = 0
        self.total_fail_case = 0
        self.total_online_fail_case = 0
        self.jsonfile_list = []
        self.result_url_list = []
        self.total_fail_case_info = {}
        self.apifox_url_list = config.apifox_url_list

    def run_command(self, command):
        """执行apifox CLI的命令"""
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d_%H-%M-%S")
        filename = "apifox-report-" + f"{date_time}"
        apifox_cli_path = "apifox"
        apifox_command = (
            f"{apifox_cli_path} run {command} -r json,cli --out-file {filename}"
        )
        # 输出到脚本目录下\apifox-reports文件夹
        # 使用subprocess运行命令
        try:
            with subprocess.Popen(
                apifox_command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            ) as proc:
                for line in proc.stdout:
                    # 正则表达式来匹配 URL
                    url_pattern = r"https://www\.apifox\.cn/link/project/\d+/api-test/test-report/\d+"
                    urls = re.findall(url_pattern, line)
                    self.result_url_list.extend(urls)
                    print(line, end="")
            # 等待子进程结束并获取返回码
            exit_code = proc.wait()
            print(f"Command finished with exit code {exit_code}")
            self.jsonfile_list.append(filename)
        except subprocess.CalledProcessError as e:
            print("{}:命令执行完成:".format(date_time))
            print(e.output.decode("utf-8"))
            self.jsonfile_list.append(filename)
        except Exception as e:
            print("{}:发生错误:".format(date_time))
            print(str(e))

    def total_test(self):
        apifox_url_list = self.apifox_url_list
        for url in apifox_url_list:
            self.run_command(url)
        for file in self.jsonfile_list:
            if file:
                result = json_analyse(file)
                if not result:
                    continue
                total_count, fail_count, result_dict, result_url = result
                self.total_case += total_count
                self.total_fail_case += fail_count
                self.total_fail_case_info.update(result_dict)
        message = f"共测试接口用例{self.total_case}条"
        if self.total_fail_case == 0:
            message += "，全部成功！\n"
        else:
            message += f"，失败{self.total_fail_case}条，失败的用例如下:\n"
            # j = 1
            # # 遍历字典的键值对并逐行输出
            # for key, value in self.total_fail_case_info.items():
            #     message += f"{j}.{key}: {value}\n"
            #     j += 1
        send_message(
            message,
            self.result_url_list,
            self.total_fail_case == 0,
            self.total_fail_case_info,
        )


if __name__ == "__main__":
    apifox_test = apifox_auto_test()
    apifox_test.total_test()
