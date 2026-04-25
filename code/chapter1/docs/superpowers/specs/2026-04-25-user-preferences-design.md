# 用户偏好功能设计

## 概述

为智能旅行助手 Agent 添加用户偏好功能，支持个性化推荐、对话式偏好管理和历史行为学习。

## 需求

1. **个性化推荐** - Agent 在推荐景点时自动参考用户偏好
2. **偏好管理交互** - 用户通过对话设置/更新偏好
3. **历史学习** - Agent 根据用户反馈推断偏好，确认后保存

## 数据结构

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

## 新增组件

### PreferenceManager 类

- `load()` / `save()` - 读写 JSON 文件
- `get_context()` - 生成偏好描述文本，供 Agent 参考
- `update(key, value)` - 更新偏好字段
- `record_feedback(recommendation, accepted)` - 记录推荐反馈
- `infer_preference()` - 从历史推断偏好，返回待确认项

### 新增工具函数

- `update_preference(key, value)` - Agent 调用更新偏好
- `show_preferences()` - 显示当前偏好
- `record_feedback(recommendation, accepted)` - 记录推荐反馈

## 系统提示扩展

在原有提示基础上增加：

```
# 用户偏好：
当前用户偏好：{preference_context}

# 偏好管理：
- 用户提到偏好时（如"我喜欢爬山"），调用 update_preference 工具记录
- 用户说"我的偏好"/"设置偏好"时，调用 show_preferences 工具
- 推荐被接受/拒绝时，调用 record_feedback 记录

# 推荐原则：
- 优先推荐符合用户偏好的景点
- 若用户偏好与天气冲突，提醒用户并给出替代方案
```

## 交互流程

### 偏好设置

```
用户: 我喜欢爬山，预算 500 左右
Agent: Thought: 用户在设置偏好
       Action: update_preference(attraction_types=["爬山"])
       Action: update_preference(budget={"max": 500})
       → 已记录您的偏好
```

### 个性化推荐

```
用户: 推荐深圳的景点
Agent: [查询天气] → [调用 get_attraction，注入偏好]
       → 根据您喜欢爬山和当前晴天，推荐：梧桐山、马峦山...
```

### 历史学习

```
用户: 这个推荐不错
Agent: Action: record_feedback(recommendation="梧桐山", accepted=True)
       → [推断：用户连续接受爬山推荐]
       → 我注意到您似乎喜欢爬山，要记住这个偏好吗？
用户: 好的
Agent: Action: update_preference(attraction_types=["爬山"])
```

## 错误处理

- JSON 文件损坏 → 使用默认偏好，提示用户
- 偏好字段缺失 → 自动补全默认值
- 无效偏好值 → 忽略并提示

## 实现方式

在 `FirstAgentTest.py` 中扩展，保持单文件结构：
1. 新增 `PreferenceManager` 类
2. 新增偏好相关工具函数
3. 扩展 Agent 系统提示
4. 修改主循环，注入偏好上下文
