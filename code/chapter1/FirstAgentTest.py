import copy
import json
from datetime import datetime
from typing import Any, Optional

class PreferenceManager:
    """
    用户偏好管理器，负责读写偏好数据、生成偏好上下文、记录反馈和推断偏好。
    """

    DEFAULT_PREFERENCES = {
        "user_id": "default",
        "preferences": {
            "attraction_types": [],
            "budget": {"min": 0, "max": None},
            "transport_mode": None,
            "activity_level": None,
            "preferred_time": None,
            "group_size": None,
            "special_requirements": []
        },
        "history": {
            "searched_cities": [],
            "accepted_recommendations": [],
            "rejected_recommendations": []
        },
        "inferred_preferences": [],
        "last_updated": "2024-01-01T00:00:00"
    }

    def __init__(self, file_path: str = "user_preferences.json"):
        self.file_path = file_path
        self.data = self.load()

    def load(self) -> dict:
        """从 JSON 文件加载偏好数据，若文件损坏则使用默认值。"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 补全缺失字段
            for key, value in self.DEFAULT_PREFERENCES.items():
                if key not in data:
                    data[key] = copy.deepcopy(value)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in data[key]:
                            data[key][sub_key] = copy.deepcopy(sub_value)
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"偏好文件加载失败，使用默认偏好: {e}")
            return copy.deepcopy(self.DEFAULT_PREFERENCES)

    def save(self) -> None:
        """保存偏好数据到 JSON 文件。"""
        try:
            self.data["last_updated"] = datetime.now().isoformat()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except (IOError, OSError) as e:
            print(f"保存偏好文件失败: {e}")

    def get_context(self) -> str:
        """生成偏好描述文本，供 Agent 推荐时参考。"""
        prefs = self.data["preferences"]
        parts = []

        if prefs["attraction_types"]:
            parts.append(f"偏好景点类型: {', '.join(prefs['attraction_types'])}")
        if prefs["budget"]["max"] is not None:
            parts.append(f"预算范围: {prefs['budget']['min']}-{prefs['budget']['max']}元")
        if prefs["transport_mode"]:
            parts.append(f"交通方式: {prefs['transport_mode']}")
        if prefs["activity_level"]:
            parts.append(f"活动强度: {prefs['activity_level']}")
        if prefs["preferred_time"]:
            parts.append(f"偏好时间: {prefs['preferred_time']}")
        if prefs["group_size"]:
            parts.append(f"出行人数: {prefs['group_size']}人")
        if prefs["special_requirements"]:
            parts.append(f"特殊需求: {', '.join(prefs['special_requirements'])}")

        if not parts:
            return "暂无用户偏好记录"
        return "\n".join(parts)

    def update(self, key: str, value: Any) -> str:
        """更新偏好字段。"""
        # 支持嵌套键，如 "budget.max"
        if "." in key:
            parent, child = key.split(".", 1)
            if parent in self.data["preferences"] and child in self.data["preferences"][parent]:
                self.data["preferences"][parent][child] = value
            else:
                return f"错误: 未知的偏好字段 '{key}'"
        elif key in self.data["preferences"]:
            self.data["preferences"][key] = value
        else:
            return f"错误: 未知的偏好字段 '{key}'"

        self.save()
        return f"已更新偏好: {key} = {value}"

    def record_feedback(self, recommendation: str, accepted: bool, city: str = None) -> str:
        """记录推荐反馈，并返回推断出的待确认偏好（如有）。"""
        history = self.data["history"]

        if city and city not in history["searched_cities"]:
            history["searched_cities"].append(city)

        feedback_entry = {
            "recommendation": recommendation,
            "city": city,
            "timestamp": datetime.now().isoformat()
        }

        if accepted:
            history["accepted_recommendations"].append(feedback_entry)
        else:
            history["rejected_recommendations"].append(feedback_entry)

        self.save()

        # 尝试推断偏好
        inferred = self.infer_preference()
        if inferred:
            return f"已记录反馈。{inferred}"
        return "已记录反馈。"

    def infer_preference(self) -> Optional[str]:
        """从历史推断偏好，返回待确认的推断结果。"""
        accepted = self.data["history"]["accepted_recommendations"]

        # 简单推断逻辑：连续接受 2 次相似类型的推荐
        if len(accepted) >= 2:
            recent = accepted[-2:]
            # 检查是否有共同的景点类型关键词
            # 这里实现简单的关键词匹配推断
            keywords = ["爬山", "公园", "海滩", "博物馆", "古镇", "自然风光", "人文景观"]
            for keyword in keywords:
                count = sum(1 for r in recent if keyword in r.get("recommendation", ""))
                if count >= 2:
                    # 检查是否已经在偏好中
                    if keyword not in self.data["preferences"]["attraction_types"]:
                        return f"我注意到您似乎喜欢{keyword}，要记住这个偏好吗？"

        return None


AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str)`: 根据城市和天气搜索推荐的旅游景点。
- `update_preference(key: str, value: str)`: 更新用户偏好。key可以是 attraction_types, budget.max, transport_mode, activity_level, preferred_time, group_size, special_requirements。
- `show_preferences()`: 显示当前用户偏好。
- `record_feedback(recommendation: str, accepted: str, city: str)`: 记录推荐反馈，accepted为"true"或"false"。

# 用户偏好:
{preference_context}

# 偏好管理规则:
- 当用户提到偏好时（如"我喜欢爬山"、"预算500元"），调用 update_preference 工具记录。
- 当用户说"我的偏好"、"查看偏好"、"设置偏好"时，调用 show_preferences 工具。
- 当用户对推荐表示满意或不满意时，调用 record_feedback 工具记录反馈。
- 推荐景点时，优先考虑用户偏好（景点类型、预算、活动强度等）。

# 输出格式要求:
你的每次回复必须严格遵循以下格式，包含一对Thought和Action：

Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]

Action的格式必须是以下之一：
1. 调用工具：function_name(arg_name="arg_value")
2. 结束任务：Finish[最终答案]

# 重要提示:
- 每次只输出一对Thought-Action
- Action必须在同一行，不要换行
- 当收集到足够信息可以回答用户问题时，必须使用 Action: Finish[最终答案] 格式结束

请开始吧！"""


import requests

def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息。
    """
    # API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"
    
    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (成功)
        response.raise_for_status() 
        # 解析返回的JSON数据
        data = response.json()
        
        # 提取当前天气状况
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        
        # 格式化成自然语言返回
        return f"{city}当前天气：{weather_desc}，气温{temp_c}摄氏度"
        
    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误：查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误：解析天气数据失败，可能是城市名称无效 - {e}"



import os
from tavily import TavilyClient

def get_attraction(city: str, weather: str) -> str:
    """
    根据城市和天气，使用Tavily Search API搜索并返回优化后的户外运动地点推荐。
    会自动参考用户偏好进行个性化推荐。
    """

    api_key = os.environ.get("TAVILY_API_KEY")

    if not api_key:
        return "错误：未配置TAVILY_API_KEY。"

    tavily = TavilyClient(api_key=api_key)

    # 获取用户偏好上下文
    preference_context = ""
    if preference_manager:
        preference_context = preference_manager.get_context()
        if preference_context != "暂无用户偏好记录":
            preference_context = f"用户偏好: {preference_context}"

    # 构造查询，包含偏好信息
    if preference_context:
        query = f"'{city}' 在'{weather}'天气下的户外运动地点推荐。{preference_context}。请推荐符合用户偏好的地点。"
    else:
        query = f"'{city}' 在'{weather}'天气下最值得去的户外运动地点推荐及理由"

    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
             return "抱歉，没有找到相关的户外运动地点推荐。"

        return "根据搜索，为您找到以下信息：\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"错误：执行Tavily搜索时出现问题 - {e}"


# 全局偏好管理器实例
preference_manager = None

def init_preference_manager(file_path: str = "user_preferences.json") -> PreferenceManager:
    """初始化偏好管理器。"""
    global preference_manager
    preference_manager = PreferenceManager(file_path)
    return preference_manager

def update_preference(key: str, value: Any) -> str:
    """
    更新用户偏好。
    key: 偏好字段名（如 attraction_types, budget.max, transport_mode）
    value: 偏好值（字符串形式，如 "爬山,公园" 或 "500"）
    """
    if not preference_manager:
        return "错误: 偏好管理器未初始化"

    # 解析值类型
    if key == "attraction_types" or key == "special_requirements":
        # 列表类型，逗号分隔
        value = [v.strip() for v in value.split(",")]
    elif key.startswith("budget"):
        # 数值类型
        try:
            value = int(value)
        except ValueError:
            try:
                value = float(value)
            except ValueError:
                return f"错误: 无法将 '{value}' 转换为数值"
    elif key == "group_size":
        try:
            value = int(value)
        except ValueError:
            return f"错误: 无法将 '{value}' 转换为整数"

    return preference_manager.update(key, value)

def show_preferences() -> str:
    """
    显示当前用户偏好。
    """
    if not preference_manager:
        return "错误: 偏好管理器未初始化"

    context = preference_manager.get_context()
    return f"当前用户偏好:\n{context}"

def record_feedback(recommendation: str, accepted: str, city: Optional[str] = None) -> str:
    """
    记录推荐反馈。
    recommendation: 推荐内容
    accepted: "true" 或 "false"
    city: 城市（可选）
    """
    if not preference_manager:
        return "错误: 偏好管理器未初始化"

    accepted_bool = accepted.lower() == "true"
    return preference_manager.record_feedback(recommendation, accepted_bool, city)


# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "update_preference": update_preference,
    "show_preferences": show_preferences,
    "record_feedback": record_feedback,
}

from openai import OpenAI

class OpenAICompatibleClient:
    """
    一个用于调用任何兼容OpenAI接口的LLM服务的客户端。
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """调用LLM API来生成回应。"""
        print("正在调用大语言模型...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("大语言模型响应成功。")
            return answer
        except Exception as e:
            print(f"调用LLM API时发生错误: {e}")
            return "错误：调用语言模型服务时出错。"

import re

def main():
    """主程序入口"""
    # --- 1. 配置LLM客户端 ---
    # 请根据您使用的服务，将这里替换成对应的凭证和地址
    API_KEY = "5da2f07f9c17af58aa2818a50d3e3468:NmZkYWJlNTc2OGI3ZWVhZGE0MDA2YTc0"
    BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
    MODEL_ID = "astron-code-latest"
    os.environ['TAVILY_API_KEY'] = "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"

    llm = OpenAICompatibleClient(
        model=MODEL_ID,
        api_key=API_KEY,
        base_url=BASE_URL
    )

    # --- 2. 初始化 ---
    # 初始化偏好管理器
    global preference_manager
    preference_manager = init_preference_manager()

    user_prompt = "你好，请帮我查询一下今天深圳的天气，然后根据天气推荐一个适合户外运动的地方。"
    prompt_history = [f"用户请求: {user_prompt}"]

    print(f"用户输入: {user_prompt}\n" + "="*40)

    # --- 3. 运行主循环 ---
    for i in range(5): # 设置最大循环次数
        print(f"--- 循环 {i+1} ---\n")

        # 3.1. 构建Prompt
        full_prompt = "\n".join(prompt_history)

        # 3.2. 调用LLM进行思考
        # 注入偏好上下文到系统提示
        current_system_prompt = AGENT_SYSTEM_PROMPT.format(
            preference_context=preference_manager.get_context()
        )
        llm_output = llm.generate(full_prompt, system_prompt=current_system_prompt)
        # 模型可能会输出多余的Thought-Action，需要截断
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 3.3. 解析并执行行动
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
            print(f"任务完成，最终答案:\n {final_answer}")
            break

        tool_name = re.search(r"(\w+)\(", action_str).group(1)
        args_str = re.search(r"\((.*)\)", action_str).group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误：未定义的工具 '{tool_name}'"

        # 3.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)


if __name__ == "__main__":
    main()
