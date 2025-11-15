from typing import Dict, Any
from langgraph.graph import CompiledGraph

class RunnableWorkflow:
    """
    一个容器类，用于封装编译好的 LangGraph 应用及其完整的元数据和接口契约。
    """
    def __init__(self,
                 name: str,
                 description: str,
                 input_schema: Dict, # <--- 新增
                 output_schema: Dict, # <--- 新增
                 graph: CompiledGraph):
        self._name = name
        self._description = description
        self._input_schema = input_schema   # <--- 新增
        self._output_schema = output_schema # <--- 新增
        self._graph = graph

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict: # <--- 新增
        """返回工作流的输入接口定义。"""
        return self._input_schema

    @property
    def output_schema(self) -> Dict: # <--- 新增
        """返回工作流的输出接口定义。"""
        return self._output_schema

    @property
    def graph(self) -> CompiledGraph:
        return self._graph

    def invoke(self, inputs: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        print(f"--- 🚀 Invoking Workflow: '{self.name}' ---")
        return self._graph.invoke(inputs, **kwargs)

    # ... stream 和 __repr__ 方法保持不变 ...