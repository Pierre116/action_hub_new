"""YAML import/export for workflow templates (V2.3)."""
import json
import yaml
from actionhub.workflow.graph import validate_graph


def yaml_to_graph(yaml_text: str) -> dict:
    """Parse YAML workflow definition into wft_graph dict.
    
    Validates result against graph schema.
    Raises ValueError with validation errors.
    """
    try:
        graph = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    if not isinstance(graph, dict):
        raise ValueError("YAML must be a dictionary")
    
    # Validate the graph structure
    errors = validate_graph(graph)
    if errors:
        raise ValueError("; ".join(errors))
    
    return graph


def graph_to_yaml(graph: dict, name_en: str, name_cn: str, wft_type: str) -> str:
    """Export a workflow template as YAML text."""
    # Add metadata to the graph
    output = {
        "name_en": name_en,
        "name_cn": name_cn,
        "type": wft_type,
        "workflow": graph
    }
    
    return yaml.dump(output, default_flow_style=False, sort_keys=False, allow_unicode=True)


def validate_yaml(yaml_text: str) -> tuple[bool, str]:
    """Validate YAML and return (is_valid, error_message)."""
    try:
        graph = yaml_to_graph(yaml_text)
        return (True, "")
    except ValueError as e:
        return (False, str(e))


def parse_import_yaml(yaml_text: str) -> dict:
    """Parse import YAML and extract metadata and graph.
    
    Returns dict with: name_en, name_cn, type, graph
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("YAML must be a dictionary with name, type, and workflow sections")
    
    # Extract metadata
    name_en = data.get("name_en", "Imported Workflow")
    name_cn = data.get("name_cn", "导入的工作流")
    wft_type = data.get("type", "action")
    
    # Extract workflow graph
    graph = data.get("workflow", data)
    
    # Validate the graph
    errors = validate_graph(graph)
    if errors:
        raise ValueError("; ".join(errors))
    
    return {
        "name_en": name_en,
        "name_cn": name_cn,
        "type": wft_type,
        "graph": graph
    }
