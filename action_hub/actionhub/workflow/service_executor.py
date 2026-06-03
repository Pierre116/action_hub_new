"""
Service Executor for Workflow V3 Service Steps
- Maintains a registry of whitelisted service handler callables
- Provides dispatch logic for auto-execution of Service steps
- Exposes handler metadata for admin tooling
"""

from typing import Callable, Dict, Any, List

class ServiceHandler:
    def __init__(self, name: str, func: Callable, input_schema: dict, output_schema: dict, description: str = ""):
        self.name = name
        self.func = func
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.description = description

    def execute(self, inputs: dict) -> dict:
        return self.func(inputs)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "description": self.description,
        }

class ServiceExecutorRegistry:
    def __init__(self):
        self._handlers: Dict[str, ServiceHandler] = {}

    def register(self, handler: ServiceHandler):
        if handler.name in self._handlers:
            raise ValueError(f"Handler '{handler.name}' already registered.")
        self._handlers[handler.name] = handler

    def get(self, name: str) -> ServiceHandler:
        return self._handlers[name]

    def list_handlers(self) -> List[dict]:
        return [h.as_dict() for h in self._handlers.values()]

    def execute(self, name: str, inputs: dict) -> dict:
        handler = self.get(name)
        return handler.execute(inputs)


# Global registry instance
service_registry = ServiceExecutorRegistry()


# Example: Register a handler that always casts inputs to int
def add_numbers(inputs: dict) -> dict:
    a = inputs.get("a", 0)
    b = inputs.get("b", 0)
    try:
        a = int(a)
    except Exception:
        a = 0
    try:
        b = int(b)
    except Exception:
        b = 0
    return {"result": a + b}

service_registry.register(ServiceHandler(
    name="add_numbers",
    func=add_numbers,
    input_schema={"a": "int", "b": "int"},
    output_schema={"result": "int"},
    description="Adds two numbers and returns the result."
))

# Module-level API for registry access
def list_handlers():
    return service_registry.list_handlers()
