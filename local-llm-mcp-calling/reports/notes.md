# Benchmark Environment Notes

## LM Studio

**Version:** `0.4.4 (Build 1)`

| Backend | Version |
|---------|---------|
| CPU llama.cpp (Windows) | v2.4.0 |
| CUDA 12 llama.cpp (Windows) | v2.4.0 |
| CUDA llama.cpp (Windows) | v2.4.0 |
| Vulkan llama.cpp (Windows) | v2.4.0 |
| Harmony (Windows) | v0.3.6 |

## Hardware

| Component | Spec |
|-----------|------|
| CPU | AMD Ryzen 7 7800X3D (8-core, x86_64, AVX/AVX2) |
| GPU | NVIDIA GeForce RTX 4080 SUPER (Discrete, CUDA) |
| VRAM | 16 GB (17,170,956,288 bytes) |
| RAM | 63 GB (67,769,708,544 bytes) |
| Total Memory | 79 GB (84,940,664,832 bytes) |
| CUDA Compute Capability | 8.9 |

## Benchmark Parameters

| Parameter | Value |
|-----------|-------|
| Context length | 8192 tokens |
| Temperature | 0.0 (set by runner, overrides LM Studio UI) |
| Max tokens | 4096 |
| Tool choice | auto |
| Task timeout | 300s wall-clock |
| Max agentic turns | 25 |

---

## Jinja Template Fix: `bytedance/seed-oss-36b`

### Problem

The v2 agentic runner failed for `bytedance/seed-oss-36b` with a Jinja template rendering error on every task. The model scored 63% in v1 singleshot (which only sends single-turn messages) but 0% in v2 agentic (which builds multi-turn conversations with tool call history).

```
Error code: 400 - {'error': 'Error rendering prompt with jinja template:
"Unknown operator "in" between ArrayValue and TupleValue"'}
```

### Root Cause

LM Studio's Jinja engine (used to render the GGUF-embedded chat template) does not support Python's `in` operator for membership testing against tuples or arrays. The original seed-oss-36b template had **three** incompatible `in` usages:

1. **`t in ("number", "integer")`** in the `py_type` macro — `in` between string and tuple literal
2. **`name in item.function.parameters.required`** in the Args section — `in` between string and array
3. **`message.role in ["user", "system"]`** in the message loop — `in` between string and array

Additionally, the original template used `{%- for item in tools if item.type == "function" %}` (inline filter on for-loop) which LM Studio also doesn't support.

### Fix Applied (3 changes)

**1. `py_type` macro** — replaced tuple membership with explicit equality:
```jinja
{# BEFORE: #}  {%- elif t in ("number", "integer") -%}int
{# AFTER:  #}  {%- elif t == "number" or t == "integer" -%}int
```

**2. Required parameter check** — replaced array membership with guarded loop:
```jinja
{# BEFORE: #}
{%- if name in item.function.parameters.required %} [必填]{% else %} [选填]{% endif %}

{# AFTER: #}
{%- set _is_req = namespace(val=false) -%}
{%- if item.function.parameters.required is defined and item.function.parameters.required is iterable -%}
  {%- for r in item.function.parameters.required -%}
    {%- if r == name -%}{%- set _is_req.val = true -%}{%- endif -%}
  {%- endfor -%}
{%- endif -%}
{%- if _is_req.val %} [必填]{% else %} [选填]{% endif %}
```

**3. Message role check** — replaced array membership with explicit equality:
```jinja
{# BEFORE: #}  {%- elif message.role in ["user", "system"] %}
{# AFTER:  #}  {%- elif message.role == "user" or message.role == "system" %}
```

**4. Tools loop** — moved inline filter inside loop body:
```jinja
{# BEFORE: #}  {%- for item in tools if item.type == "function" %}
{# AFTER:  #}  {%- for item in tools %}
               {%- if item.type is defined and item.type == "function" %}
```

### Impact

- v1 singleshot was **not affected** (single-turn messages never triggered the template bugs)
- v2 agentic was **completely broken** (0% on all 28 tasks) — rerun with fixed template required
- The `is defined` guard on `item.function.parameters.required` also fixed a secondary error (`"Expected iterable or object type in for loop: got UndefinedValue"`) for tools without a `required` field

### Full Fixed Template

```jinja
{# ----------‑‑‑ special token variables ‑‑‑---------- #}
{%- set bos_token              = '<seed:bos>'               -%}
{%- set eos_token              = '<seed:eos>'               -%}
{%- set pad_token              = '<seed:pad>'               -%}
{%- set toolcall_begin_token   = '<seed:tool_call>'         -%}
{%- set toolcall_end_token     = '</seed:tool_call>'        -%}
{%- set think_begin_token      = '<seed:think>'             -%}
{%- set think_end_token        = '</seed:think>'            -%}
{%- set budget_begin_token     = '<seed:cot_budget_reflect>'-%}
{%- set budget_end_token       = '</seed:cot_budget_reflect>'-%}
{# -------------- reflection-interval lookup -------------- #}
{%- if not thinking_budget is defined %}
{%- set thinking_budget = -1 -%}
{%- else -%}
{%- set thinking_budget = thinking_budget | int -%}
{%- endif -%}
{%- set budget_keys_v05 = [0, 512, 1024, 2048, 4096, 8192, 16384] -%}
{%- set budget_values_v05 = [0, 128, 256, 512, 512, 1024, 1024] -%}
{%- set ns = namespace(interval = None) -%}
{%- for i in range(budget_keys_v05|length) -%}
    {%- if ns.interval is none and thinking_budget <= budget_keys_v05[i] -%}
        {%- set ns.interval = budget_values_v05[i] -%}
    {%- endif -%}
{%- endfor -%}
{%- if ns.interval is none -%}
    {%- set ns.interval = budget_values_v05[-1] -%}
{%- endif -%}
{# ---------- Preprocess the system message ---------- #}
{%- if messages[0]["role"] == "system" %}
{%- set system_message = messages[0]["content"] %}
{%- set loop_messages = messages[1:] %}
{%- else %}
{%- set loop_messages = messages %}
{%- endif %}
{# ---------- Ensure tools exist ---------- #}
{%- if not tools is defined or tools is none %}
{%- set tools = [] %}
{%- endif %}
{# tools2doc.jinja #}
{%- macro py_type(t) -%}
    {%- if t == "string" -%}str
    {%- elif t == "number" or t == "integer" -%}int
    {%- elif t == "boolean" -%}bool
    {%- elif t == "array" -%}list
    {%- else -%}Any{%- endif -%}
{%- endmacro -%}
{# ---------- Output the system block ---------- #}
{%- if system_message is defined %}
{{ bos_token + "system\n" + system_message }}
{%- else %}
{%- if tools is iterable and tools | length > 0 %}
{{ bos_token + "system\nYou are Doubao, a helpful AI assistant. You may call one or more functions to assist with the user query." }}
{%- endif %}
{%- endif %}
{%- if use_json_tooldef is defined and use_json_tooldef %}

{{"Tool List:\nYou are authorized to use the following tools (described in JSON Schema format). Before performing any task, you must decide how to call them based on the descriptions and parameters of these tools."}}
{{ tools | tojson(ensure_ascii=False) }}
{%- else %}
{%- for item in tools %}
{%- if item.type is defined and item.type == "function" %}


Function:
def {{ item.function.name }}(
{%- for name, spec in item.function.parameters.properties.items() %}
        {{- name }}: {{ py_type(spec.type) }}{% if not loop.last %},{% endif %}
{%- endfor %}):
    """
    {{ item.function.description | trim }}

    {# ---------- Args ---------- #}
    {%- if item.function.parameters.properties %}
    Args:
    {%- for name, spec in item.function.parameters.properties.items() %}

    - {{ name }} ({{ py_type(spec.type) }})
      {%- set _is_req = namespace(val=false) -%}
      {%- if item.function.parameters.required is defined and item.function.parameters.required is iterable -%}
        {%- for r in item.function.parameters.required -%}
          {%- if r == name -%}{%- set _is_req.val = true -%}{%- endif -%}
        {%- endfor -%}
      {%- endif -%}
      {%- if _is_req.val %} [必填]{% else %} [选填]{% endif %}
      {{- " " ~ (spec.description or "") }}
    {%- endfor %}
    {%- endif %}

    {# ---------- Returns ---------- #}
    {%- if item.function.returns is defined
          and item.function.returns.properties is defined
          and item.function.returns.properties %}
    Returns:
    {%- for name, spec in item.function.returns.properties.items() %}

    - {{ name }} ({{ py_type(spec.type) }}):
      {{- " " ~ (spec.description or "") }}
    {%- endfor %}
    {%- endif %}

    """
{%- endif %}
{%- endfor %}
{%- endif %}
{%- if tools is iterable and tools | length > 0 %}

{{"工具调用请遵循如下格式:\n<seed:tool_call>\n<function=example_function_name>\n<parameter=example_parameter_1>value_1</parameter>\n<parameter=example_parameter_2>This is the value for the second parameter\nthat can span\nmultiple lines</parameter>\n</function>\n</seed:tool_call>\n"}}
{%- endif %}
{# End the system block line #}
{%- if system_message is defined or tools is iterable and tools | length > 0 %}
{{ eos_token }}
{%- endif %}
{# ---------- Thinking Budget ---------- #}
{%- if thinking_budget is defined %}
{%- if thinking_budget == 0 %}
{{ bos_token+"system" }}
{{ "You are an intelligent assistant that can answer questions in one step without the need for reasoning and thinking, that is, your thinking budget is 0. Next, please skip the thinking process and directly start answering the user's questions." }}
{{ eos_token }}
{%- elif not thinking_budget == -1 %}
{{ bos_token+"system" }}
{{ "You are an intelligent assistant with reflective ability. In the process of thinking and reasoning, you need to strictly follow the thinking budget, which is "}}{{thinking_budget}}{{". That is, you need to complete your thinking within "}}{{thinking_budget}}{{" tokens and start answering the user's questions. You will reflect on your thinking process every "}}{{ns.interval}}{{" tokens, stating how many tokens have been used and how many are left."}}
{{ eos_token }}
{%- endif %}
{%- endif %}
{# ---------- List the historical messages one by one ---------- #}
{%- for message in loop_messages %}
{%- if message.role == "assistant"
  and message.tool_calls is defined
  and message.tool_calls is iterable
  and message.tool_calls | length > 0 %}
{{ bos_token + message.role }}
{%- if message.reasoning_content is defined and message.reasoning_content is string and message.reasoning_content | trim | length > 0 %}
{{ "\n" + think_begin_token + message.reasoning_content | trim + think_end_token }}
{%- endif %}
{%- if message.content is defined and message.content is string and message.content | trim | length > 0 %}
{{ "\n" + message.content | trim + "\n" }}
{%- endif %}
{%- for tool_call in message.tool_calls %}
{%- if tool_call.function is defined %}{% set tool_call = tool_call.function %}{% endif %}
{{ "\n" + toolcall_begin_token + "\n<function=" + tool_call.name + ">\n" }}
{%- if tool_call.arguments is defined %}
{%- for arg_name, arg_value in tool_call.arguments | items %}
{{ "<parameter=" + arg_name + ">" }}
{%- set arg_value = arg_value if arg_value is string else arg_value | string %}
{{ arg_value+"</parameter>\n" }}
{%- endfor %}
{%- endif %}
{{ "</function>\n" + toolcall_end_token }}
{%- endfor %}
{{ eos_token }}
{%- elif message.role == "user" or message.role == "system" %}
{{ bos_token + message.role + "\n" + message.content + eos_token }}
{%- elif message.role == "assistant" %}
{{ bos_token + message.role }}
{%- if message.reasoning_content is defined and message.reasoning_content is string and message.reasoning_content | trim | length > 0 %}
{{ "\n" + think_begin_token + message.reasoning_content | trim + think_end_token }}
{%- endif %}
{%- if message.content is defined and message.content is string and message.content | trim | length > 0 %}
{{ "\n" + message.content | trim + eos_token }}
{%- endif %}
{# Include the tool role #}
{%- else %}
{{ bos_token + message.role + "\n" + message.content + eos_token }}
{%- endif %}
{%- endfor %}
{# ---------- Control the model to start continuation ---------- #}
{%- if add_generation_prompt %}
{{ bos_token+"assistant\n" }}
{%- if thinking_budget == 0 %}
{{ think_begin_token + "\n" + budget_begin_token + "The current thinking budget is 0, so I will directly start answering the question." + budget_end_token + "\n" + think_end_token }}
{%- endif %}
{%- endif %}
```
