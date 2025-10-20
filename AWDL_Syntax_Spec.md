# AWDL Syntax Specification (v0.1)

---

## 1. Overview

AWDL (Agent Workflow Description Language) is a **domain-specific language (DSL)** for describing multi-agent workflows in the HAWK system.

It provides a concise, declarative way to define:
- **Tasks** (Agent invocations)
- **Data flow** between tasks
- **Control flow** (conditional, parallel, synchronization, and so on)
- **Input and output variables**

AWDL scripts can be compiled into agent framework like **LangGraph, AutoGen, Swarm** and executed by **HAWK Agent runtimes**.  
This allows users to describe complex agent collaborations using a human-readable, high-level syntax.

---

## 2. Basic Structure

An AWDL script is organized into three parts: one or more `workflow` blocks, and one or more `agent` blocks, optional blocks for `toolNode`(only accessible in limited agent framework), optional block for router `router` and tools should be defined in `tools.py`,`routers.py` . Users only need to declare the required tools and routers in the AWDL file and add them to the workflow.

### General form

```awdl
workflow <workflow_name> {
    input { ... }
    {tasks { ... }}
    output { ... }
}
agent <agent_name> {
		input {...}
		description {...}
		model {...}
		system_prompt {...}
		tools {...}
		output {...}
}
toolNode <toolNode_name>{
		tool {...}
}
router <router_name>{
		router {...}
}
```

Each `workflow` contains:
- **input**: declare workflow parameters.
- **tasks**: define task sequence and dependencies, implemented by agent or tools.
- **output**: declare final outputs.

Each `agent` contains:

- **input**: declare agent input parameters.
- **description**: the natrual language description of the function of the agent.
- **model**: the backbone language model of the agent.
- **system_prompt**: the system prompt of the agent.
- **output**: the output declaration of the agent.
- **tools** (optional): the tools available for the agent.

Each `toolNode` contains:

- **tool**: the backbone tool defined in `tools.py`

Each `router` contains:

- **router**: the router defined in `routers.py`

### Example

```awdl
workflow "OnlineSearchFlow" {

    input {
        string topic
    }
    
		addSeq {essayFile, SearchAgent}
		addSeq {SearchAgent, SummarizeAgent}

    output {
        String summary = SummarizeAgent.output
    }
}

agent SearchAgent{
		input {
				string topic
		}
		description "An agent which is capable to search information online"
		model "GPT-4-Turbo"
		system_prompt "you are a search agent. You can use the searchOnline tool to search for information and pass it to the SummarizeAgent."
		output {
		string searchResult
		}
		tools searchOnline
}

agent SummarizeAgent{
		input {
				string searchResult
		}
		description "An agent which is capable to summarize the information and answer the question."
		model "GPT-4-Turbo"
		system_prompt "you are a search agent. You can use the searchOnline tool to search for information and answer the user's question."
		output {
				string sumamry
		}
}
```

---

## 3. Keywords and Components

| Keyword | Description | Example |
|----------|--------------|---------|
| `workflow` | Define a named workflow | `workflow "ResearchPipeline" {...}` |
| `input` | Declare input parameters | `input { String topic }` |
| `output`       | Define workflow outputs                                      | `output { String summary = SummarizeAgent.output }` |
| `await`        | Synchronize after parallel tasks                             | `await { task A, task B }`                          |
| `addParallel` | Add parallel tasks in the system | `addParallel par{ task A, task B }` |
| `addSeq`       | Add a sequential relation between agents/ tools/ functions   | `addSeq {SearchAgent, SummarizeAgent}`              |
| `addVote`      | Add a group that votes for the final answer by several agents | `addVote {group_name, agent_1,agent_2,...}`         |
| `addConSeq`    | Add a conditional sequence between agents/tools/functions    | `addConSeq{agent,router}`                           |
| `addGroupChat` | Add a group between agents to discuss the final answer       | `addGroupChat{group_name,agen_1,agent_2}`           |
| `addMerge`     | Add a result merge of the parallel operation                 | `addMerge{agent,par}`                               |



---

## 4. Type System

AWDL provides a simple type system for input/output variables.

| Type | Description | Example |
|------|--------------|----------|
| `Int` | Integer | `Int count = 5` |
| `Float` | Floating-point number | `Float x = 3.14` |
| `String` | Text value | `String name = "Alice"` |
| `Bool` | Boolean value | `Bool ready = true` |
| `List[T]` | Ordered collection | `List[String] names = ["A", "B"]` |
| `Dict[K,V]` | Key-value mapping | `Dict[String,Int] scores = { "math": 90 }` |
| `File` | File object | `File report = "output.pdf"` |
| `Struct` | User-defined structure | `Struct Paper { title: String, url: String }` |

---

## 5. Control Flow

### Conditional Branch

The conditional branch is implemented by router, which defines the condition for conditional branch

```awdl
def router(input):
  if (input.mode == "fast") {
      call QuickAgent
  } else {
      call SafeAgent
  }
```

### Parallel Execution

```awdl
parallel {
    TaskA
    TaskB
}
```

### Synchronization
```awdl
await { TaskA, TaskB }
call CombineResults
```

---

## 6. Task and Agent Invocation

Each agent/function defined should be connected with system input or former output through keywords like `addSeq`,`addConSeq`

### Syntax

```awdl
addSeq {<input>, <next>}
addConSeq {<input>, <router>}
```

### Example
```awdl
addSeq {input, first_agent}
addSeq {first_agent, first_function}
addSeq {first_function, second_agent}
```

- `agentName` corresponds to an Agent class in MICA.  
- Parameters inside `{}` are key-value pairs.
- if the `input` is an agent or a function, then it will be translated into the output of the agent (or the function) as the input of the sequence

---

## 7. Input and Output Blocks

### Input Block
Defines parameters passed into the workflow.
```awdl
input {
    String topic
    Int limit
}
```

### Output Block
Defines what data is returned at the end.
```awdl
output {
    String summary = SummarizeAgent.output
}
```

---

## 8. Example Scripts

### Example 1 — Minimal Workflow
```awdl
workflow "HelloAgent" {
    input {
        String name
    }

    addSeq{name, GreetAgent}
		
    output {
        String message = GreetAgent.output
    }
}
```

### Example 2 — Sequential Agents
```awdl
workflow "OnlineSearchFlow" {

    input {
        string topic
    }
    
		addSeq {essayFile, SearchAgent}
		addSeq {SearchAgent, SummarizeAgent}

    output {
        String summary = SummarizeAgent.output
    }
}
```

### Example 3 — Parallel Execution
```awdl
workflow "ParallelExample" {
    input {
        String query
    }

    addParallel parallel_1{
        task WebSearchAgent { 
        		input{string query}
        		addSeq{query,WebSearchAgent}
        		output{string WebSearchAgent.output}
        }
        task ScholarSearchAgent {
        		input{string query}
        		addSeq{query,ScholarSearchAgent}
        		output{string ScholarSearchAgent.output}
        }
    }

    addMerge{SummarizeAgent,parallel_1}

    output {
        String result = SummarizeAgent.output
    }
}
```

---

## 9. Summary

AWDL provides a **high-level, human-readable DSL** for orchestrating multi-agent workflows within the HAWK system.

- Executed through the **LangGraph/Autogen/CrewAI...** runtime  
- Designed for **clarity**, **modularity**, and **extensibility**  

Future work will include:
- Parser implementation (AWDL → JSON/AST → LangGraph)
- GUI integration for visual workflow editing
- Static analysis for type checking and dependency validation
