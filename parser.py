import yaml
import os
from abc import ABC
from difflib import get_close_matches
from typing import List, Dict, Text
from dataclasses import dataclass

class WorkflowParser:
    def __init__(self):
        self.node_v = NodeValidator()
        self.edge_v = EdgeValidator()
        self.base_v = BaseValidator()
        self.base_v.valid_keys = {'version', 'workflow', 'state', 'nodes', 'edges'}
        self.specs = {
            "version": TypeSpec(str),
            "workflow": TypeSpec(dict),
            "state": TypeSpec(dict),
            "nodes": TypeSpec(list),
            "edges": TypeSpec(list)
        }

    def parse_file(self, file_path: str) -> Dict:
        if not os.path.exists(file_path): 
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            try: 
                data = yaml.safe_load(f)
            except yaml.YAMLError as e: 
                raise ValueError(f"YAML Syntax Error: {e}")
        return self._validate(data)

    def _validate(self, data):
        if not isinstance(data, dict): 
            raise WorkflowValidationError([ValidationError("Basic", "Root must be dict", "root")])
        
        all_errors = []

        all_errors.extend(self.base_v.validate_required_keys(data, {'workflow', 'state', 'nodes', 'edges'}, "root"))
        all_errors.extend(self.base_v.validate_spelling(data, "root"))
        all_errors.extend(self.base_v.validate_type(data, "root", self.specs))

        state_keys = set()
        if isinstance(data.get('state'), dict):
            state_keys = set(data['state'].keys())

        node_names = set()
        if isinstance(data.get('nodes'), list):
            node_names = set(n.get('name') for n in data['nodes'] if isinstance(n, dict) and 'name' in n)

        context = {'state_keys': state_keys, 'node_names': node_names}

        if isinstance(data.get('nodes'), list):
            for i, n in enumerate(data['nodes']):
                if isinstance(n, dict):
                    all_errors.extend(self.node_v.validate(n, f"nodes[{i}]", context))

        if isinstance(data.get('edges'), list):
            for i, e in enumerate(data['edges']):
                if isinstance(e, dict):
                    all_errors.extend(self.edge_v.validate(e, f"edges[{i}]", context))

        if all_errors:
            raise WorkflowValidationError(all_errors)
            
        return data

@dataclass
class ValidationError:
    rule_name: Text
    message: Text
    path: Text

class WorkflowValidationError(Exception):
    def __init__(self, errors: List[ValidationError]):
        self.errors = errors
        self.message = f"Found {len(errors)} validation errors."
        super().__init__(self.message)

    def __str__(self):
        return "\n".join([f"❌ [{e.rule_name}] at '{e.path}': {e.message}" for e in self.errors])

class TypeSpec:
    def __init__(self, expected_type, nullable=False, nested_schema=None):
        self.expected_type = expected_type
        self.nullable = nullable
        self.nested_schema = nested_schema or {}

class BaseValidator(ABC):
    def __init__(self): self.valid_keys = set()
    
    def validate_required_keys(self, content, required_keys, path):
        errors = []
        for key in required_keys:
            if key not in content:
                errors.append(ValidationError("RequiredKeyValidation", f"Missing required key '{key}'", path))
        return errors

    def validate_spelling(self, content, path):
        errors = []
        if "*" in self.valid_keys: return errors
        for key in content:
            if key not in self.valid_keys:
                matches = get_close_matches(key, self.valid_keys, n=3, cutoff=0.6)
                sugg = f"Did you mean: {', '.join(matches)}" if matches else ""
                errors.append(ValidationError("SpellingValidation", f"Unknown key '{key}'. {sugg}", path))
        return errors

    def validate_type(self, content, path, type_specs):
        errors = []
        def _val(val, spec, curr_path):
            errs = []
            if val is None:
                if not spec.nullable: errs.append(ValidationError("TypeValidation", "Value cannot be null", curr_path))
                return errs
            if not isinstance(val, spec.expected_type):
                errs.append(ValidationError("TypeValidation", f"Expected {spec.expected_type.__name__}, got {type(val).__name__}", curr_path))
                return errs
            if isinstance(val, dict) and spec.nested_schema:
                for k, v in val.items():
                    if k in spec.nested_schema: errs.extend(_val(v, spec.nested_schema[k], f"{curr_path}.{k}"))
            return errs
        
        for k, v in content.items():
            if k in type_specs: errors.extend(_val(v, type_specs[k], f"{path}.{k}" if path else k))
        return errors

class NodeValidator(BaseValidator):
    def __init__(self):
        super().__init__()
        self.valid_keys = {'name', 'type', 'tool', 'model', 'system_prompt', 'input_mapping', 'output_mapping'}
        self.type_specs = {
            "name": TypeSpec(str), "type": TypeSpec(str), "tool": TypeSpec(str), "system_prompt": TypeSpec(str),
            "input_mapping": TypeSpec(dict), "output_mapping": TypeSpec(dict),
            "model": TypeSpec(dict, nested_schema={"provider": TypeSpec(str), "name": TypeSpec(str)})
        }
    def validate(self, node, path, context):
        errors = []
        errors.extend(self.validate_required_keys(node, {'name', 'type'}, path))
        if errors: return errors
        
        if node['type'] == 'toolNode': errors.extend(self.validate_required_keys(node, {'tool'}, path))
        elif node['type'] == 'agent': errors.extend(self.validate_required_keys(node, {'model', 'system_prompt'}, path))
        else: errors.append(ValidationError("ValueValidation", f"Invalid type '{node.get('type')}'", f"{path}.type"))
        
        errors.extend(self.validate_spelling(node, path))
        errors.extend(self.validate_type(node, path, self.type_specs))
        
        if 'input_mapping' in node and isinstance(node['input_mapping'], dict):
            for k, v in node['input_mapping'].items():
                if isinstance(v, str) and v.startswith("state.") and v.split(".")[1] not in context['state_keys']:
                    errors.append(ValidationError("ReferenceValidation", f"State var '{v}' undefined", f"{path}.input_mapping.{k}"))
        return errors

class EdgeValidator(BaseValidator):
    def __init__(self):
        super().__init__()
        self.valid_keys = {'from', 'to'}
        self.type_specs = {"from": TypeSpec(str), "to": TypeSpec(str)}
    def validate(self, edge, path, context):
        errors = []
        errors.extend(self.validate_required_keys(edge, {'from', 'to'}, path))
        errors.extend(self.validate_spelling(edge, path))
        errors.extend(self.validate_type(edge, path, self.type_specs))
        if errors: return errors
        valid_nodes = context['node_names'] | {'__start__', '__end__', '__output__'}
        if edge['from'] not in valid_nodes: errors.append(ValidationError("ReferenceValidation", f"Node '{edge['from']}' undefined", f"{path}.from"))
        if edge['to'] not in valid_nodes: errors.append(ValidationError("ReferenceValidation", f"Node '{edge['to']}' undefined", f"{path}.to"))
        return errors