### **LangGraph 编译器 DSL 设计文档 v1.0.0**



#### 1. 概述与设计哲学

本文档定义了一种用于声明式构建 LangGraph 应用的配置语言。该语言旨在实现以下目标：

*   **可读性**: 配置应易于人类阅读和编写，即使对于不熟悉 LangGraph 内部实现的开发者也是如此。
*   **声明式**: 用户应专注于描述工作流的“什么（What）”，而不是“如何（How）”。
*   **表现力**: DSL 应能充分表达 LangGraph 的核心概念，包括状态、节点、条件边（路由）和工具使用。
*   **可扩展性**: 整体设计应易于扩展，以便未来支持新的节点类型或 LangGraph 特性。

本文档支持 **JSON** 和 **YAML** 两种格式。为清晰起见，所有示例将使用 YAML。

`注：本版本的初级目标是实现node、tool和graph，更多的memory等等在后面实现`

#### 2. 通用原则

*   **命名规范**: 所有用户定义的名称（如 `workflow.name`, `node.name`）应使用蛇形命名法（snake\_case），且必须是字母、数字和下划线的组合，并以字母开头。
*   **大小写**: 所有关键字（如 `type`, `model`, `provider`）均为小写。
*   **状态引用**: 在配置中引用工作流状态（State）中的变量时，应使用点表示法 `state.variable_name` 的字符串形式。编译器负责解析这些字符串并生成相应的代码。

#### 3. 顶层结构

一个有效的配置文件必须包含以下顶层键：

| 键         | 类型         | 是否必需 | 描述                                                       |
| :--------- | :----------- | :------- | :--------------------------------------------------------- |
| `version`  | string       | 是       | 配置文件的语义化版本，如 `"1.0.0"`。用于未来的兼容性管理。 |
| `workflow` | object       | 是       | 定义工作流的元数据，如名称和输入/输出接口。                |
| `state`    | object       | 是       | 声明工作流的完整状态（State）对象。                        |
| `nodes`    | list[object] | 是       | 定义工作流中的所有节点。                                   |
| `edges`    | list[object] | 是       | 定义节点之间的连接关系。                                   |

---

#### 4. 详细规范

##### 4.1 `workflow` 对象

此对象定义了整个图的边界和元数据。对应的是model.py中的RunnableWorkflow，是我们对LangGraph中的CompiledGraph的封装，使得每一个图可以有自己的名字、简介，方便用户自定义。`input_schema`和`output_schema`

| 键              | 类型   | 是否必需 | 描述                                                     |
| :-------------- | :----- | :------- | :------------------------------------------------------- |
| `name`          | string | 是       | 工作流的唯一名称。                                       |
| `description`   | string | 否       | 对工作流功能的简要描述。                                 |
| `input_schema`  | object | 否       | 定义工作流的输入。键为变量名，值为类型字符串（见下文）。 |
| `output_schema` | object | 否       | 定义工作流的输出。键为变量名，值为类型字符串（见下文）。 |

**支持的类型字符串**: `"string"`, `"integer"`, `"float"`, `"boolean"`, `"list"`, `"dict"`。

**示例**:
```yaml
workflow:
  name: research_and_report_workflow
  description: "一个用于进行网络研究并生成报告的代理工作流"
  input_schema:
    topic: "string"
  output_schema:
    final_report: "string"
```


##### 4.2 `state` 对象

此对象声明了 LangGraph 的 `StateGraph` 所需的所有变量及其类型。

*   **结构**: 一个简单的键值对对象，键为状态变量名，值为其类型字符串。
*   **规则**: `workflow.input_schema` 和 `workflow.output_schema` 中定义的所有变量都**必须**在 `state` 中声明。

**示例**:
```yaml
state:
  topic: "string"
  search_results: "list"
  report_draft: "string"
  final_report: "string"
```

##### 4.3 `nodes` 列表

这是 DSL 的核心，定义了工作流中的所有计算单元。它是一个对象列表，每个对象代表一个节点。

**所有节点的通用字段**:

| 键     | 类型   | 是否必需 | 描述                                                         |
| :----- | :----- | :------- | :----------------------------------------------------------- |
| `name` | string | 是       | 节点的唯一名称，用于在 `edges` 中引用。                      |
| `type` | string | 是       | 节点的类型。决定了该对象需要哪些其他字段。支持的类型见下文。 |

---

###### 4.3.1 节点类型: `agent`

代表一个由 LLM 驱动、可使用工具的代理节点。

| 键               | 类型         | 是否必需 | 描述                                                         |
| :--------------- | :----------- | :------- | :----------------------------------------------------------- |
| `model`          | object       | 是       | 定义语言模型。包含 `provider` (e.g., "openai") 和 `name` (e.g., "gpt-4-turbo")。 |
| `system_prompt`  | string       | 是       | 代理的系统提示词。支持使用 `{state.variable}` 语法进行模板化。 |
| `tools`          | list[string] | 否       | 此代理节点可调用的工具名称列表。                             |
| `input_mapping`  | object       | 是       | 将状态变量映射到提示词模板中的变量。键为模板变量，值为状态引用。 |
| `output_mapping` | object       | 是       | 将代理的输出（通常是字符串）映射回状态变量。键为状态变量，值为固定的 `"__output__"`。 |

**示例**:
```yaml
- name: report_writer_agent
  type: agent
  model:
    provider: "openai"
    name: "gpt-4-turbo"
  system_prompt: "你是一个研究员。请根据以下资料撰写报告：{report_data}"
  input_mapping:
    report_data: "state.search_results"
  output_mapping:
    state.report_draft: "__output__"
```

###### 4.3.2 节点类型: `toolNode`

代表一个执行单个工具的节点。

| 键               | 类型   | 是否必需 | 描述                                                         |
| :--------------- | :----- | :------- | :----------------------------------------------------------- |
| `tool`           | string | 是       | 要执行的工具的名称。                                         |
| `input_mapping`  | object | 是       | 将状态变量映射到工具的输入参数。键为工具参数名，值为状态引用。 |
| `output_mapping` | object | 是       | 将工具的执行结果映射回状态变量。键为状态变量，值为固定的 `"__output__"`。 |

tool肯定没法用yaml写，所以parser和compiler最好加一个识别工具.py的功能，main中加入-t tools_example.py这样的写法

**示例**:
```yaml
- name: web_search_node
  type: toolNode
  tool: "tavily_search"
  input_mapping:
    query: "state.topic"
  output_mapping:
    state.search_results: "__output__"
```

###### 4.3.3 节点类型: `router`

代表一个条件路由节点，用于决定工作流的下一个走向。

| 键          | 类型   | 是否必需 | 描述                                                         |
| :---------- | :----- | :------- | :----------------------------------------------------------- |
| `condition` | string | 是       | 一个可被安全求值的 Python 表达式字符串。表达式中可以使用 `state` 对象。 |
| `paths`     | object | 是       | 一个键值对对象。键是 `condition` 表达式可能返回的字符串值，值是下一个节点的名称。 |

**安全警告**: `condition` 的执行必须在一个受限的沙箱环境中进行，以防止任意代码执行。`eval()` 的直接使用是不安全的。

**示例**:
```yaml
- name: quality_check_router
  type: router
  condition: "'FINAL' if len(state.report_draft) > 500 else 'REVISE'"
  paths:
    FINAL: "publish_report_node" # 假设存在这个节点
    REVISE: "report_writer_agent" # 返回去修改
```

##### 4.4 `edges` 列表

此列表定义了节点之间的有向连接。

*   **结构**: 一个对象列表，每个对象代表一条边。
*   **特殊关键字**:
    *   `__start__`: 代表工作流的入口点。
    *   `__end__`: 代表工作流的结束点。

| 键     | 类型   | 是否必需 | 描述                                                         |
| :----- | :----- | :------- | :----------------------------------------------------------- |
| `from` | string | 是       | 边的起始节点名称。可以是 `__start__` 或任意已定义节点的 `name`。 |
| `to`   | string | 是       | 边的目标节点名称。可以是 `__end__` 或任意已定义节点的 `name`。 |

**注意**: 对于 `router` 节点的输出边，不需要在这里定义。`router` 的 `paths` 字段已经隐式定义了其条件边。`edges` 中只需要定义指向 `router` 节点的边。

**示例**:
```yaml
edges:
  - from: "__start__"
    to: "web_search_node"
  - from: "web_search_node"
    to: "report_writer_agent"
  - from: "report_writer_agent"
    to: "quality_check_router"
  - from: "publish_report_node" # 假设这是最终节点
    to: "__end__"
```

---

#### 5. 完整示例 (`workflow.yml`)

```yaml
version: "1.0.0"

workflow:
  name: "tech_research_agent"
  description: "An agent that researches a tech topic and writes a brief report."
  input_schema:
    topic: "string"
  output_schema:
    final_report: "string"

state:
  topic: "string"
  search_results: "list"
  report_draft: "string"
  final_report: "string"

nodes:
  - name: search_for_topic
    type: toolNode
    tool: "tavily_search"
    input_mapping:
      query: "state.topic"
    output_mapping:
      state.search_results: "__output__"

  - name: write_initial_report
    type: agent
    model:
      provider: "openai"
      name: "gpt-4-turbo"
    system_prompt: >
      You are a tech analyst. Based on the following search results, 
      write a concise report of about 100 words.
      Search Results: {results}
    input_mapping:
      results: "state.search_results"
    output_mapping:
      state.report_draft: "__output__"

  - name: review_and_finalize_router
    type: router
    condition: "'PASS' if 'error' not in state.report_draft.lower() and len(state.report_draft) > 80 else 'FAIL'"
    paths:
      PASS: "finalize_report_node"
      FAIL: "__end__" # 如果报告太短或有错误，直接结束

  - name: finalize_report_node
    type: agent # 可以用另一个 agent 来做最终格式化
    model:
      provider: "openai"
      name: "gpt-3.5-turbo"
    system_prompt: "Format the following draft into a final report. Just output the text. DRAFT: {draft}"
    input_mapping:
      draft: "state.report_draft"
    output_mapping:
      state.final_report: "__output__"

edges:
  - from: "__start__"
    to: "search_for_topic"
  - from: "search_for_topic"
    to: "write_initial_report"
  - from: "write_initial_report"
    to: "review_and_finalize_router"
  - from: "finalize_report_node"
    to: "__end__"
```