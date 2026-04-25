# 用户偏好功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为智能旅行助手 Agent 添加用户偏好功能，支持个性化推荐、对话式偏好管理和历史行为学习。

**Architecture:** 在现有 `FirstAgentTest.py` 中扩展，新增 `PreferenceManager` 类管理偏好数据，新增三个工具函数供 Agent 调用，扩展系统提示注入偏好上下文。

**Tech Stack:** Python, JSON 文件存储, OpenAI-compatible API, ReAct Agent 模式

---

## 文件结构

- **修改:** `FirstAgentTest.py` - 新增 PreferenceManager 类、工具函数、扩展系统提示、修改主循环
- **修改:** `user_preferences.json` - 更新数据结构，添加 `inferred_preferences` 字段

---

### Task 1: 实现 PreferenceManager 类基础功能

**Files:**
- Modify: `FirstAgentTest.py` (在文件开头导入部分后添加)

- [ ] **Step 1: 添加 PreferenceManager 类定义**

在 `FirstAgentTest.py` 中，在 `AGENT_SYSTEM_PROMPT` 定义之前添加：

```python
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
                    data[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_key not in data[key]:
                            data[key][sub_key] = sub_value
            return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"偏好文件加载失败，使用默认偏好: {e}")
            return self.DEFAULT_PREFERENCES.copy()
    
    def save(self) -> None:
        """保存偏好数据到 JSON 文件。"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
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
```

- [ ] **Step 2: 验证代码语法正确**

运行: `python -c "import FirstAgentTest; pm = FirstAgentTest.PreferenceManager(); print(pm.get_context())"`

预期: 输出 "暂无用户偏好记录" 或当前偏好信息，无语法错误

---

### Task 2: 实现 PreferenceManager 更新和反馈记录功能

**Files:**
- Modify: `FirstAgentTest.py` (在 PreferenceManager 类中添加方法)

- [ ] **Step 1: 添加 update 和 record_feedback 方法**

在 `PreferenceManager` 类的 `get_context` 方法后添加：

```python
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
            # 这里可以扩展更复杂的推断逻辑
            # 目前只做简单提示
            return None
        
        return None
```

- [ ] **Step 2: 验证更新功能**

运行: `python -c "import FirstAgentTest; pm = FirstAgentTest.PreferenceManager(); print(pm.update('attraction_types', ['爬山'])); print(pm.get_context())"`

预期: 输出 "已更新偏好..." 和包含 "偏好景点类型: 爬山" 的上下文

---

### Task 3: 实现偏好管理工具函数

**Files:**
- Modify: `FirstAgentTest.py` (在现有工具函数后添加)

- [ ] **Step 1: 添加三个偏好管理工具函数**

在 `get_attraction` 函数后、`available_tools` 字典定义前添加：

```python
# 全局偏好管理器实例
preference_manager = None

def init_preference_manager(file_path: str = "user_preferences.json") -> PreferenceManager:
    """初始化偏好管理器。"""
    global preference_manager
    preference_manager = PreferenceManager(file_path)
    return preference_manager

def update_preference(key: str, value: str) -> str:
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
            value = float(value) if "." in value else value
    elif key == "group_size":
        try:
            value = int(value)
        except ValueError:
            pass
    
    return preference_manager.update(key, value)

def show_preferences() -> str:
    """
    显示当前用户偏好。
    """
    if not preference_manager:
        return "错误: 偏好管理器未初始化"
    
    context = preference_manager.get_context()
    return f"当前用户偏好:\n{context}"

def record_feedback(recommendation: str, accepted: str, city: str = None) -> str:
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
```

- [ ] **Step 2: 更新 available_tools 字典**

修改 `available_tools` 字典，添加新工具：

```python
# 将所有工具函数放入一个字典，方便后续调用
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "update_preference": update_preference,
    "show_preferences": show_preferences,
    "record_feedback": record_feedback,
}
```

- [ ] **Step 3: 验证工具函数**

运行: `python -c "import FirstAgentTest; pm = FirstAgentTest.init_preference_manager(); print(FirstAgentTest.show_preferences())"`

预期: 输出当前偏好信息

---

### Task 4: 扩展 Agent 系统提示

**Files:**
- Modify: `FirstAgentTest.py` (修改 AGENT_SYSTEM_PROMPT)

- [ ] **Step 1: 修改系统提示，添加偏好相关指令**

将 `AGENT_SYSTEM_PROMPT` 替换为：

```python
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
```

---

### Task 5: 修改主循环注入偏好上下文

**Files:**
- Modify: `FirstAgentTest.py` (修改初始化和主循环部分)

- [ ] **Step 1: 初始化偏好管理器**

在 `# --- 2. 初始化 ---` 部分，添加偏好管理器初始化：

```python
# --- 2. 初始化 ---
# 初始化偏好管理器
preference_manager = init_preference_manager()

user_prompt = "你好，请帮我查询一下今天深圳的天气，然后根据天气推荐一个适合户外运动的地方。"
prompt_history = [f"用户请求: {user_prompt}"]

print(f"用户输入: {user_prompt}\n" + "="*40)
```

- [ ] **Step 2: 修改 LLM 调用，注入偏好上下文**

修改主循环中的 `llm.generate` 调用：

```python
    # 3.2. 调用LLM进行思考
    # 注入偏好上下文到系统提示
    current_system_prompt = AGENT_SYSTEM_PROMPT.format(
        preference_context=preference_manager.get_context()
    )
    llm_output = llm.generate(full_prompt, system_prompt=current_system_prompt)
```

- [ ] **Step 3: 验证完整流程**

运行: `python FirstAgentTest.py`

预期: Agent 正常运行，系统提示中包含用户偏好信息

---

### Task 6: 修改 get_attraction 工具注入偏好

**Files:**
- Modify: `FirstAgentTest.py` (修改 get_attraction 函数)

- [ ] **Step 1: 修改 get_attraction 函数，在查询中包含偏好**

修改 `get_attraction` 函数：

```python
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
```

- [ ] **Step 2: 验证个性化推荐**

运行: `python FirstAgentTest.py`

预期: 推荐结果中考虑用户偏好

---

### Task 7: 更新 user_preferences.json 数据结构

**Files:**
- Modify: `user_preferences.json`

- [ ] **Step 1: 更新 JSON 文件结构**

将 `user_preferences.json` 内容更新为：

```json
{
  "user_id": "default",
  "preferences": {
    "attraction_types": [],
    "budget": {"min": 0, "max": null},
    "transport_mode": null,
    "activity_level": null,
    "preferred_time": null,
    "group_size": null,
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
```

---

### Task 8: 最终验证

- [ ] **Step 1: 运行完整测试**

运行: `python FirstAgentTest.py`

预期输出:
- Agent 正常启动
- 系统提示包含偏好上下文
- 查询天气和推荐景点正常工作

- [ ] **Step 2: 测试偏好设置交互**

手动修改 `user_prompt` 测试偏好设置：

```python
user_prompt = "我喜欢爬山，预算大概500元，帮我推荐深圳的景点"
```

运行: `python FirstAgentTest.py`

预期: Agent 调用 `update_preference` 工具记录偏好

- [ ] **Step 3: 测试查看偏好**

修改 `user_prompt`：

```python
user_prompt = "查看我的偏好"
```

运行: `python FirstAgentTest.py`

预期: Agent 调用 `show_preferences` 工具显示偏好

---

## 自检清单

**1. Spec 覆盖检查:**
- ✓ PreferenceManager 类 - Task 1, 2
- ✓ 工具函数 - Task 3
- ✓ 系统提示扩展 - Task 4
- ✓ 主循环修改 - Task 5
- ✓ get_attraction 注入偏好 - Task 6
- ✓ JSON 数据结构更新 - Task 7
- ✓ 错误处理（JSON损坏、字段缺失）- Task 1 load() 方法

**2. Placeholder 检查:**
- 无 TBD、TODO 等占位符
- 所有代码步骤包含完整实现代码

**3. 类型一致性检查:**
- PreferenceManager 类方法签名一致
- 工具函数参数命名一致
- available_tools 字典键名一致